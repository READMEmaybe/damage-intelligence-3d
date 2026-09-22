"""Benchmark runner for the extraction engine.

Usage:
    uv run run_benchmark.py majority_baseline          # evaluate an approach
    uv run run_benchmark.py majority_baseline --full   # score on all 1,000 cases
    uv run run_benchmark.py --validate                 # dataset sanity checks

Writes results/predictions/<approach>.json and results/metrics_<approach>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.extraction import data as d
from src.extraction import metrics as m
from src.extraction.approaches.base import Approach, MajorityBaseline
from src.extraction.approaches.classical_ml import ClassicalMLApproach
from src.extraction.approaches.hybrid import HybridApproach
from src.extraction.approaches.llm import LLMApproach
from src.extraction.approaches.rule_based import RuleBasedApproach
from src.extraction.ontology import ExtractionResult

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PRED_DIR = RESULTS_DIR / "predictions"
METRICS_DIR = RESULTS_DIR / "metrics"

APPROACHES: dict[str, callable] = {
    MajorityBaseline.name: lambda cases, gts: MajorityBaseline(gts),
    RuleBasedApproach.name: lambda cases, gts: RuleBasedApproach(),
    ClassicalMLApproach.name: lambda cases, gts: ClassicalMLApproach(cases, gts),
    LLMApproach.name: lambda cases, gts: LLMApproach(),
    HybridApproach.name: lambda cases, gts: HybridApproach(),
}


def get_approach(name: str, train_cases: list[d.Case], train_gts: list[d.GroundTruth]) -> Approach:
    factory = APPROACHES.get(name)
    if factory is None:
        raise SystemExit(f"unknown approach {name!r}; known: {sorted(APPROACHES)}")
    return factory(train_cases, train_gts)


def run_validate() -> None:
    cases, gts = d.load_dataset()
    problems = d.validate_dataset(cases, gts)
    if problems:
        print(f"dataset problems: {len(problems)}")
        for p in problems[:20]:
            print(" -", p)
        raise SystemExit(1)
    print(json.dumps(d.corpus_stats(gts), indent=1, ensure_ascii=False))
    print("dataset OK: 1000 cases validated")


def run_benchmark(name: str, full: bool) -> None:
    cases, gts = d.load_dataset()
    problems = d.validate_dataset(cases, gts)
    if problems:
        print(f"dataset problems: {len(problems)}", file=sys.stderr)
        for p in problems[:20]:
            print(" -", p, file=sys.stderr)
        raise SystemExit(1)

    split = d.make_split(gts)
    if full:
        score_ids = sorted(split["train_ids"] + split["test_ids"])
    else:
        score_ids = sorted(split["test_ids"])

    by_id = {c.id: c for c in cases}
    gt_by_id = {g.case_id: g for g in gts}
    train_ids = sorted(split["train_ids"])

    approach = get_approach(name, [by_id[i] for i in train_ids], [gt_by_id[i] for i in train_ids])
    print(f"running {approach} on {len(score_ids)} cases")

    t0 = time.time()
    preds: list[ExtractionResult | None] = []
    if approach.max_workers > 1:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=approach.max_workers) as pool:
            futures = [pool.submit(approach.extract, by_id[cid]) for cid in score_ids]
            for cid, fut in zip(score_ids, futures):
                try:
                    preds.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    preds.append(None)
                    print(f"  case {cid} failed: {exc}", file=sys.stderr)
    else:
        for cid in score_ids:
            try:
                preds.append(approach.extract(by_id[cid]))
            except Exception as exc:  # noqa: BLE001
                preds.append(None)
                print(f"  case {cid} failed: {exc}", file=sys.stderr)
    latency = time.time() - t0

    op_stats = {
        "latency_total_s": round(latency, 2),
        "latency_per_case_ms": round(1000 * latency / len(score_ids), 2),
        "cases_scored": len(score_ids),
    }
    op_stats.update(approach.op_stats())

    metrics = m.score(preds, [gt_by_id[cid] for cid in score_ids], op_stats)

    tag = f"{name}_full" if full else name
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    pred_file = PRED_DIR / f"{tag}.json"
    pred_file.write_text(
        json.dumps([p.model_dump() if p else None for p in preds], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    metrics_file = METRICS_DIR / f"{tag}.json"
    metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=1))
    print(f"predictions -> {pred_file}")
    print(f"metrics     -> {metrics_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase A extraction benchmark")
    parser.add_argument("approach", nargs="?", help="approach name (see APPROACHES)")
    parser.add_argument("--full", action="store_true", help="score all 1,000 cases instead of the 200-case holdout")
    parser.add_argument("--validate", action="store_true", help="dataset validation + corpus stats")
    args = parser.parse_args()

    if args.validate or not args.approach:
        run_validate()
    else:
        run_benchmark(args.approach, args.full)


if __name__ == "__main__":
    main()
