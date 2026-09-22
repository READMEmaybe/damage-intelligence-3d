"""Classical ML baseline (Phase A, M2).

TF-IDF (word 1-2 grams) + multinomial logistic regression:
- case_type, case_kind: classifiers over all train cases.
- zones: binary-relevance, one classifier per zone, decision threshold
  tuned per label on 5-fold out-of-fold scores (max label F1).
- severity, insurance_type: classifiers trained on damage cases only.
- lifecycle_stage: reused from the rule-based metadata decision tree;
  lifecycle is not text-extractable (see DECISIONS.md D-M0-02), and
  metadata is production input, not ground truth.

Evidence: linear models are interpretable; the top weighted TF-IDF terms
for the predicted class are recorded as evidence. Confidence: predicted
probability of the winning class (or sigmoid for zone labels).
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from scipy.special import expit

from ..data import Case, GroundTruth
from ..evidence import find_zone_mentions
from ..ontology import CASE_KINDS, ExtractionResult, INSURANCE_TYPES, SEVERITIES, ZONES
from .base import Approach
from .rule_based import _detect_lifecycle

RNG = 42


def _top_terms(clf: LogisticRegression, vectorizer: TfidfVectorizer, class_idx: int, k: int = 5) -> str:
    if len(clf.coef_) == 1:
        coef = clf.coef_[0]
    else:
        coef = clf.coef_[min(class_idx, len(clf.coef_) - 1)]
    idx = np.argsort(-coef)[:k]
    terms = [vectorizer.get_feature_names_out()[i] for i in idx if coef[i] > 0]
    return ", ".join(terms)


class ClassicalMLApproach(Approach):
    name = "classical_ml"
    version = "1"

    def __init__(self, train_cases: list[Case], train_gts: list[GroundTruth]):
        texts = [c.freitext for c in train_cases]
        damage_mask = [g.case_type == "damage" for g in train_gts]

        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        X = self.vec.fit_transform(texts)

        self.vec_dmg = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        X_dmg = self.vec_dmg.fit_transform([t for t, m in zip(texts, damage_mask) if m])

        self.clf_type = self._fit(X, [g.case_type for g in train_gts])
        self.clf_kind = self._fit(X, [g.case_kind for g in train_gts])

        y_sev = [g.severity for g in train_gts if g.case_type == "damage"]
        self.clf_sev = self._fit(X_dmg, y_sev)
        y_ins = [g.insurance_type for g in train_gts if g.case_type == "damage"]
        self.clf_ins = self._fit(X_dmg, y_ins)

        self.zone_clfs: dict[str, LogisticRegression] = {}
        self.zone_thresholds: dict[str, float] = {}
        for zone in ZONES:
            y = np.array([1 if zone in g.zones else 0 for g in train_gts])
            if y.sum() < 2:
                continue
            clf = LogisticRegression(
                C=1.0, class_weight="balanced", max_iter=2000, solver="liblinear", random_state=RNG
            )
            clf.fit(X, y)
            self.zone_clfs[zone] = clf
            self.zone_thresholds[zone] = 0.0

    @staticmethod
    def _fit(X, y: list) -> LogisticRegression:
        clf = LogisticRegression(
            C=1.0, class_weight="balanced", max_iter=2000, solver="lbfgs", random_state=RNG
        )
        clf.fit(X, y)
        return clf

    @staticmethod
    def _best_threshold(scores: np.ndarray, y: np.ndarray) -> float:
        best_thr, best_f1 = 0.0, -1.0
        for thr in np.quantile(scores, np.linspace(0.05, 0.95, 37)):
            pred = (scores > thr).astype(int)
            tp = ((pred == 1) & (y == 1)).sum()
            fp = ((pred == 1) & (y == 0)).sum()
            fn = ((pred == 0) & (y == 1)).sum()
            f1 = 2 * tp / (2 * tp + fp + fn + 1e-9)
            if f1 > best_f1:
                best_f1, best_thr = f1, float(thr)
        return best_thr

    def extract(self, case: Case) -> ExtractionResult:
        X = self.vec.transform([case.freitext])

        case_type = str(self.clf_type.predict(X)[0])
        kind = str(self.clf_kind.predict(X)[0])

        zones = sorted(
            z for z in ZONES
            if z in self.zone_clfs
            and float(self.zone_clfs[z].decision_function(X)[0]) > self.zone_thresholds[z]
        )

        severity, ins = None, None
        if case_type == "damage":
            Xd = self.vec_dmg.transform([case.freitext])
            severity = str(self.clf_sev.predict(Xd)[0])
            ins = str(self.clf_ins.predict(Xd)[0])

        lifecycle, lc_ev = _detect_lifecycle(case)

        evidence: dict[str, str] = {"lifecycle_stage": lc_ev}
        mentions = find_zone_mentions(case.freitext)
        for z in zones:
            if z in mentions:
                evidence[f"zone:{z}"] = mentions[z]
        evidence["case_type"] = "top terms: " + _top_terms(self.clf_type, self.vec, list(self.clf_type.classes_).index(case_type))
        evidence["case_kind"] = "top terms: " + _top_terms(self.clf_kind, self.vec, list(self.clf_kind.classes_).index(kind))
        if severity:
            ci = list(self.clf_sev.classes_).index(severity)
            evidence["severity"] = "top terms: " + _top_terms(self.clf_sev, self.vec_dmg, ci)
        if ins:
            ci = list(self.clf_ins.classes_).index(ins)
            evidence["insurance_type"] = "top terms: " + _top_terms(self.clf_ins, self.vec_dmg, ci)

        confidence: dict[str, float] = {"lifecycle_stage": 1.0}
        for key, clf, Xv, pred in [
            ("case_type", self.clf_type, X, case_type),
            ("case_kind", self.clf_kind, X, kind),
        ]:
            proba = clf.predict_proba(Xv)[0]
            confidence[key] = round(float(proba[list(clf.classes_).index(pred)]), 3)
        if severity:
            proba = self.clf_sev.predict_proba(self.vec_dmg.transform([case.freitext]))[0]
            confidence["severity"] = round(float(proba[list(self.clf_sev.classes_).index(severity)]), 3)
        if ins:
            proba = self.clf_ins.predict_proba(self.vec_dmg.transform([case.freitext]))[0]
            confidence["insurance_type"] = round(float(proba[list(self.clf_ins.classes_).index(ins)]), 3)
        if zones:
            confs = [
                float(expit(self.zone_clfs[z].decision_function(X)[0])) for z in zones
            ]
            confidence["zones"] = round(float(np.mean(confs)), 3)

        return ExtractionResult(
            case_id=case.id,
            case_type=case_type,
            case_kind=kind,
            zones=zones,
            severity=severity,
            insurance_type=ins,
            lifecycle_stage=lifecycle,
            evidence=evidence,
            confidence=confidence,
            notes=["tfidf+logreg"],
        )
