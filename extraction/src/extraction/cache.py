"""Disk cache for inference results (brief §16).

Cache key = sha256(freitext + approach + approach_version + schema_version).
Avoids re-running identical inference across benchmark runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .ontology import ExtractionResult

CACHE_DIR = Path(__file__).resolve().parents[2] / "results" / "cache"
SCHEMA_VERSION = "1"


def cache_key(freitext: str, approach: str, approach_version: str) -> str:
    raw = "\x00".join((freitext, approach, approach_version, SCHEMA_VERSION))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ResultCache:
    def __init__(self, approach: str, approach_version: str, cache_dir: Path | None = None):
        self.approach = approach
        self.version = approach_version
        self.dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def _path(self, freitext: str) -> Path:
        return self.dir / f"{cache_key(freitext, self.approach, self.version)}.json"

    def get(self, freitext: str) -> ExtractionResult | None:
        p = self._path(freitext)
        if not p.exists():
            self.misses += 1
            return None
        try:
            data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.misses += 1
            return None
        self.hits += 1
        return ExtractionResult.model_validate(data)

    def put(self, freitext: str, result: ExtractionResult) -> None:
        self._path(freitext).write_text(
            result.model_dump_json(indent=1), encoding="utf-8"
        )

    def stats(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses}
