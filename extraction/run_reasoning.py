"""Phase B reasoning runner (PB-M2..M4).

Usage:
    uv run run_reasoning.py --limit 30          # first 30 damage cases (smoke)
    uv run run_reasoning.py --cases 823107,888308
    uv run run_reasoning.py --all               # all 1,000 cases (canonical contract)

Writes results/reasoning/actions_full.json (viewer contract, brief §12)
and results/reasoning/ops.json (operational stats + distribution).
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.extraction import data as d
from src.reasoning.contract import confidence_band
from src.reasoning.llm import DeepSeekReasoner
from src.reasoning.pipeline import PhaseBPipeline

RESULTS_DIR = Path(__file__).resolve().parent / "results" / "reasoning"


def distribution(results: list) -> dict:
    actions: Counter = Counter()
    sources: Counter = Counter()
    bands: Counter = Counter()
    statuses: Counter = Counter()
    n_damage = 0
    for r in results:
        statuses[r.status] += 1
        if not r.damages:
            continue
        n_damage += 1
        for a in r.damages:
            actions[a.action] += 1
            sources[a.action_source] += 1
            bands[confidence_band(a.confidence)] += 1
    total = sum(actions.values())
    return {
        "damage_cases": n_damage,
        "zone_decisions": total,
        "action_%": {k: round(100 * v / total, 1) for k, v in actions.most_common()},
        "source_%": {k: round(100 * v / total, 1) for k, v in sources.most_common()},
        "confidence_bands": dict(bands),
        "statuses": dict(statuses),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase B repair/replace/assess reasoning")
    parser.add_argument("--limit", type=int, default=None, help="process the first N damage cases")
    parser.add_argument("--cases", type=str, default=None, help="comma-separated case ids")
    parser.add_argument("--all", action="store_true", help="process all 1,000 cases")
    args = parser.parse_args()

    cases, gts = d.load_dataset()
    by_id = {c.id: c for c in cases}
    gt_by_id = {g.case_id: g for g in gts}

    if args.cases:
        ids = [int(x) for x in args.cases.split(",")]
        selected = [by_id[i] for i in ids]
    elif args.limit:
        selected = [c for c, g in zip(cases, gts) if g.case_type == "damage"][: args.limit]
    else:
        selected = cases

    reasoner = DeepSeekReasoner()
    pipeline = PhaseBPipeline(reasoner)
    print(f"running Phase B on {len(selected)} cases "
          f"({'explicit pass + DeepSeek' if reasoner else 'explicit pass only'})")

    t0 = time.time()
    results = []
    if reasoner.max_workers > 1:
        with ThreadPoolExecutor(max_workers=reasoner.max_workers) as pool:
            futures = [pool.submit(pipeline.run_case, c) for c in selected]
            for c, fut in zip(selected, futures):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    print(f"  case {c.id} failed: {exc}")
    else:
        for c in selected:
            results.append(pipeline.run_case(c))
    latency = time.time() - t0

    ops = {
        "latency_total_s": round(latency, 2),
        "latency_per_case_ms": round(1000 * latency / len(selected), 2),
        "cases_processed": len(selected),
    }
    ops.update(reasoner.op_stats())
    ops["distribution"] = distribution(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "actions_full.json").write_text(
        json.dumps([r.model_dump() for r in results], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    (RESULTS_DIR / "ops.json").write_text(
        json.dumps(ops, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(json.dumps(ops, ensure_ascii=False, indent=1))
    print(f"output -> {RESULTS_DIR / 'actions_full.json'}")


if __name__ == "__main__":
    main()
