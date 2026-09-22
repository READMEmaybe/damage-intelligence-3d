"""Dataset loading, ground-truth model, validation and the fixed train/test split."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from .ontology import CASE_KIND_SET, CASE_TYPES, INSURANCE_TYPES, LIFECYCLE_STAGES, SEVERITIES, ZONE_SET

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "kit" / "dataset"
CASES_FILE = DATA_DIR / "da-cases.json"

SPLIT_SEED = 20260918
SPLIT_TEST_SIZE = 0.2
SPLIT_FILE = Path(__file__).resolve().parents[2] / "results" / "split.json"


@dataclass(frozen=True)
class GroundTruth:
    case_id: int
    case_type: str
    case_kind: str
    zones: tuple[str, ...] = ()
    severity: str | None = None
    insurance_type: str | None = None
    lifecycle_stage: str | None = None

    def zone_set(self) -> frozenset[str]:
        return frozenset(self.zones)


@dataclass(frozen=True)
class Case:
    """Production inputs only; never `ground_truth` (brief D01/D02)."""

    id: int
    freitext: str
    in_open_list: bool = False
    canceled_at: str | None = None
    completion_date_time: str | None = None
    reparation_start_date_time: str | None = None
    reparation_end_date_time: str | None = None
    states: tuple[tuple[int, str, str, bool], ...] = field(default_factory=tuple)

    @property
    def first_state(self) -> tuple[int, str, str, bool] | None:
        return self.states[0] if self.states else None


def _parse_gt(raw: dict, case_id: int) -> GroundTruth:
    gt = GroundTruth(
        case_id=case_id,
        case_type=raw["case_type"],
        case_kind=raw["case_kind"],
        zones=tuple(raw.get("zones") or ()),
        severity=raw.get("severity"),
        insurance_type=raw.get("insurance_type"),
        lifecycle_stage=raw.get("lifecycle_stage"),
    )
    return gt


def load_cases(path: Path | str | None = None) -> list[dict]:
    p = Path(path) if path else CASES_FILE
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_dataset(path: Path | str | None = None) -> tuple[list[Case], list[GroundTruth]]:
    raw = load_cases(path)
    cases: list[Case] = []
    gts: list[GroundTruth] = []
    for c in raw:
        cases.append(
            Case(
                id=c["id"],
                freitext=c["freitext"],
                in_open_list=bool(c.get("in_open_list")),
                canceled_at=c.get("canceled_at"),
                completion_date_time=c.get("completion_date_time"),
                reparation_start_date_time=c.get("reparation_start_date_time"),
                reparation_end_date_time=c.get("reparation_end_date_time"),
                states=tuple(
                    (s["id"], s["name"], s["category"], bool(s["is_done"]))
                    for s in (c.get("states") or [])
                ),
            )
        )
        gts.append(_parse_gt(c["ground_truth"], c["id"]))
    return cases, gts


def validate_dataset(cases: list[Case], gts: list[GroundTruth]) -> list[str]:
    """Structural checks. Raises nothing; returns problem list."""
    problems: list[str] = []
    if len(cases) != 1000 or len(gts) != 1000:
        problems.append(f"expected 1000 cases, got {len(cases)}/{len(gts)}")
    if len(cases) != len(gts):
        problems.append(f"case/gt length mismatch {len(cases)} vs {len(gts)}")
    texts = [c.freitext for c in cases]
    if len(set(texts)) != len(texts):
        problems.append("freitext texts are not all distinct")
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("case ids are not unique")
    for i, (c, g) in enumerate(zip(cases, gts)):
        if c.id != g.case_id:
            problems.append(f"index {i}: case id {c.id} != gt id {g.case_id}")
        if g.case_type not in CASE_TYPES:
            problems.append(f"case {c.id}: case_type {g.case_type!r} invalid")
        if g.case_kind not in CASE_KIND_SET:
            problems.append(f"case {c.id}: case_kind {g.case_kind!r} invalid")
        bad = [z for z in g.zones if z not in ZONE_SET]
        if bad:
            problems.append(f"case {c.id}: zones {bad} invalid")
        if g.severity is not None and g.severity not in SEVERITIES:
            problems.append(f"case {c.id}: severity {g.severity!r} invalid")
        if g.insurance_type is not None and g.insurance_type not in INSURANCE_TYPES:
            problems.append(f"case {c.id}: insurance {g.insurance_type!r} invalid")
        if g.lifecycle_stage is not None and g.lifecycle_stage not in LIFECYCLE_STAGES:
            problems.append(f"case {c.id}: lifecycle {g.lifecycle_stage!r} invalid")
        if g.case_type == "service" and g.zones:
            problems.append(f"case {c.id}: service case has zones {g.zones}")
        if g.case_type == "damage" and not g.zones:
            problems.append(f"case {c.id}: damage case has no zones")
        if g.case_type == "service" and g.severity is not None:
            problems.append(f"case {c.id}: service case has severity")
    return problems


def corpus_stats(gts: list[GroundTruth]) -> dict:
    from collections import Counter

    return {
        "n_cases": len(gts),
        "case_type": dict(Counter(g.case_type for g in gts)),
        "case_kind": dict(Counter(g.case_kind for g in gts)),
        "severity": dict(Counter(g.severity for g in gts)),
        "insurance_type": dict(Counter(g.insurance_type for g in gts)),
        "lifecycle_stage": dict(Counter(g.lifecycle_stage for g in gts)),
        "zone_mentions_total": sum(len(g.zones) for g in gts),
        "damage_cases_with_multiple_zones": sum(
            1 for g in gts if g.case_type == "damage" and len(g.zones) > 1
        ),
    }


def make_split(
    gts: list[GroundTruth],
    test_size: float = SPLIT_TEST_SIZE,
    seed: int = SPLIT_SEED,
    split_file: Path | None = SPLIT_FILE,
) -> dict:
    """Fixed stratified 80/20 split by case_kind x severity.

    Saved to disk so every approach scores the same holdout.
    Returns {"train_ids": [...], "test_ids": [...], "seed": ..., "test_size": ...}.
    """
    rng = random.Random(seed)
    strata: dict[tuple[str, str], list[int]] = {}
    for g in gts:
        strata.setdefault((g.case_kind, g.severity or ""), []).append(g.case_id)
    train_ids: list[int] = []
    test_ids: list[int] = []
    for ids in strata.values():
        shuffled = ids[:]
        rng.shuffle(shuffled)
        n_test = max(1, round(len(shuffled) * test_size))
        test_ids.extend(shuffled[:n_test])
        train_ids.extend(shuffled[n_test:])
    split = {
        "train_ids": sorted(train_ids),
        "test_ids": sorted(test_ids),
        "seed": seed,
        "test_size": test_size,
    }
    if split_file is not None:
        split_file.parent.mkdir(parents=True, exist_ok=True)
        split_file.write_text(json.dumps(split, indent=1), encoding="utf-8")
    return split


def load_split(split_file: Path = SPLIT_FILE) -> dict:
    return json.loads(split_file.read_text(encoding="utf-8"))
