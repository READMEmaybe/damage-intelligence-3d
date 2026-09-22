"""Evaluation metrics per brief §9.

Scoring semantics (fixed once, so approaches are comparable):
- case_type / case_kind / lifecycle_stage: all 1,000 cases.
- zones: multi-label over all cases (service cases expect the empty set).
  Exact-match accuracy reported for damage cases and for the full corpus.
- severity / insurance_type: scored on damage cases only; a missing
  prediction on a damage case counts as wrong.
- Operational counters: invalid outputs, unknown labels, review rate, etc.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

import numpy as np

from .data import GroundTruth
from .ontology import CASE_KINDS, CASE_TYPES, ExtractionResult, INSURANCE_TYPES, LIFECYCLE_STAGES, SEVERITIES, ZONES

MICRO_LABELS = CASE_TYPES
KIND_LABELS = CASE_KINDS
SEVERITY_LABELS = SEVERITIES
INSURANCE_LABELS = INSURANCE_TYPES
LIFECYCLE_LABELS = LIFECYCLE_STAGES


def _prf(y_true: Iterable[str], y_pred: Iterable[str], labels: tuple[str, ...]) -> dict[str, Any]:
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    for t, p in zip(y_true, y_pred):
        if p == t:
            tp[t] += 1
        else:
            fn[t] += 1
            if p in labels:
                fp[p] += 1
    per_class: dict[str, dict[str, float]] = {}
    for label in labels:
        n_tp, n_fp, n_fn = tp[label], fp[label], fn[label]
        prec = n_tp / (n_tp + n_fp) if n_tp + n_fp else 0.0
        rec = n_tp / (n_tp + n_fn) if n_tp + n_fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_class[label] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "support": sum(1 for t in y_true if t == label)}
    n = sum(len(v) for v in [list(y_true)])
    macro_p = np.mean([per_class[l]["precision"] for l in labels])
    macro_r = np.mean([per_class[l]["recall"] for l in labels])
    macro_f1 = np.mean([per_class[l]["f1"] for l in labels])
    acc = sum(1 for t, p in zip(y_true, y_pred) if t == p) / n if n else 0.0
    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "per_class": per_class,
        "n": n,
    }


def _multilabel_prf(y_true: list[set[str]], y_pred: list[set[str]], labels: tuple[str, ...]) -> dict[str, Any]:
    tp = fp = fn = 0
    per_label: dict[str, dict[str, float]] = {}
    for label in labels:
        l_tp = sum(1 for t, p in zip(y_true, y_pred) if label in p and label in t)
        l_fp = sum(1 for t, p in zip(y_true, y_pred) if label in p and label not in t)
        l_fn = sum(1 for t, p in zip(y_true, y_pred) if label not in p and label in t)
        tp += l_tp
        fp += l_fp
        fn += l_fn
        prec = l_tp / (l_tp + l_fp) if l_tp + l_fp else 0.0
        rec = l_tp / (l_tp + l_fn) if l_tp + l_fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_label[label] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}
    micro_p = tp / (tp + fp) if tp + fp else 0.0
    micro_r = tp / (tp + fn) if tp + fn else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    macro_p = np.mean([per_label[l]["precision"] for l in labels])
    macro_r = np.mean([per_label[l]["recall"] for l in labels])
    macro_f1 = np.mean([per_label[l]["f1"] for l in labels])
    exact = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return {
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "exact_match": exact,
        "exact_match_accuracy": round(exact / len(y_true), 4) if y_true else 0.0,
        "per_label": per_label,
    }


def _confusion(y_true: list[str], y_pred: list[str], labels: tuple[str, ...]) -> list[list[int]]:
    idx = {l: i for i, l in enumerate(labels)}
    cm = [[0] * len(labels) for _ in range(len(labels))]
    for t, p in zip(y_true, y_pred):
        cm[idx.get(t, -1)][idx.get(p, -1)] += 1
    return cm


def _acc_of(y_true: list[str], y_pred: list[str]) -> float:
    return sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true) if y_true else 0.0


def score(
    preds: list[ExtractionResult | None],
    gts: list[GroundTruth],
    op_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score predictions against ground truth.

    `preds` must align with `gts` by index; None means the approach produced
    no valid prediction for that case (counted as failed + wrong everywhere).
    """
    pred_map: dict[int, ExtractionResult] = {}
    for i, p in enumerate(preds):
        if p is not None and p.case_id != gts[i].case_id:
            raise ValueError(f"index {i}: prediction case_id {p.case_id} != gt {gts[i].case_id}")
        if p is not None:
            pred_map[p.case_id] = p

    n_failed = sum(1 for p in preds if p is None)

    # ---- case_type (all cases) ----
    ct_true, ct_pred = [], []
    for g in gts:
        p = pred_map.get(g.case_id)
        ct_true.append(g.case_type)
        ct_pred.append(p.case_type if p and p.case_type else "")
    case_type = _prf(ct_true, ct_pred, CASE_TYPES)

    # ---- case_kind (all cases) ----
    ck_true, ck_pred = [], []
    for g in gts:
        p = pred_map.get(g.case_id)
        ck_true.append(g.case_kind)
        ck_pred.append(p.case_kind if p and p.case_kind else "")
    case_kind = _prf(ck_true, ck_pred, CASE_KINDS)

    # ---- zones (multi-label, all cases; service expects empty set) ----
    z_true: list[set[str]] = [set(g.zones) for g in gts]
    z_pred: list[set[str]] = [
        set(pred_map[g.case_id].zones) if g.case_id in pred_map else set() for g in gts
    ]
    zones = _multilabel_prf(z_true, z_pred, ZONES)
    damage_idx = [i for i, g in enumerate(gts) if g.case_type == "damage"]
    zones_damage = _multilabel_prf(
        [z_true[i] for i in damage_idx], [z_pred[i] for i in damage_idx], ZONES
    )
    zones["damage_only_exact_match_accuracy"] = zones_damage["exact_match_accuracy"]
    zones["damage_only_exact_match"] = zones_damage["exact_match"]

    # ---- severity (damage cases only) ----
    sev_true: list[str] = []
    sev_pred: list[str] = []
    for i in damage_idx:
        g = gts[i]
        p = pred_map.get(g.case_id)
        sev_true.append(g.severity or "")
        sev_pred.append(p.severity if p and p.severity else "")
    severity = {
        "accuracy": round(_acc_of(sev_true, sev_pred), 4),
        "confusion_matrix": _confusion(sev_true, sev_pred, SEVERITIES),
        "labels": list(SEVERITIES),
        "n": len(sev_true),
    }

    # ---- insurance_type (damage cases only) ----
    ins_true: list[str] = []
    ins_pred: list[str] = []
    for i in damage_idx:
        g = gts[i]
        p = pred_map.get(g.case_id)
        ins_true.append(g.insurance_type or "")
        ins_pred.append(p.insurance_type if p and p.insurance_type else "")
    insurance = {
        "accuracy": round(_acc_of(ins_true, ins_pred), 4),
        "confusion_matrix": _confusion(ins_true, ins_pred, INSURANCE_TYPES),
        "labels": list(INSURANCE_TYPES),
        "n": len(ins_true),
    }
    # insurance predicted on service cases (false positives on non-damage)
    ins_leak = sum(
        1 for g in gts if g.case_type == "service" and (pred_map.get(g.case_id) and pred_map[g.case_id].insurance_type)
    )
    insurance["service_cases_with_insurance_predicted"] = ins_leak

    # ---- lifecycle_stage (all cases) ----
    lc_true = [g.lifecycle_stage or "" for g in gts]
    lc_pred = [p.lifecycle_stage if (p := pred_map.get(g.case_id)) and p.lifecycle_stage else "" for g in gts]
    lifecycle = _prf(lc_true, lc_pred, LIFECYCLE_LABELS)

    # ---- operational counters ----
    invalid_outputs = sum(1 for p in preds if p and p.validate_against_ontology())
    unknown_labels = invalid_outputs
    review_rate = sum(1 for p in preds if p and p.status == "needs_review")
    operational = {
        "n_predictions": len(preds),
        "n_failed": n_failed,
        "n_invalid_outputs": invalid_outputs,
        "n_unknown_labels": unknown_labels,
        "n_needs_review": review_rate,
        "review_rate": round(review_rate / len(preds), 4) if preds else 0.0,
    }
    if op_stats:
        operational.update(op_stats)

    return {
        "case_type": case_type,
        "case_kind": case_kind,
        "zones": zones,
        "severity": severity,
        "insurance_type": insurance,
        "lifecycle_stage": lifecycle,
        "operational": operational,
    }
