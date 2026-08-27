"""Golden-set evaluation.

BAi sells correctness. Correctness that is not measured is a claim, not a
product. Every product ships a versioned golden set; CI blocks merge when
accuracy regresses more than the threshold. This module is the scorer.

Two things it reports that an aggregate score hides:
  * per-field precision/recall/F1 — the field that matters most is often the
    one an average conceals
  * confidence calibration — when the system says 80%, is it right 80% of the
    time? A miscalibrated score is worse than none, because the escalation
    boundary and the UI both depend on it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "EvalReport",
    "FieldScore",
    "GoldenCase",
    "Prediction",
    "RegressionError",
    "evaluate",
    "load_golden_set",
    "score_field",
]


class RegressionError(AssertionError):
    """Accuracy fell further than the gate permits."""


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """One annotated example. ``expected`` maps field name to correct value."""

    case_id: str
    inputs: dict[str, Any]
    expected: dict[str, Any]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class Prediction:
    case_id: str
    produced: dict[str, Any]
    confidence: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FieldScore:
    field_name: str
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        d = self.true_positives + self.false_positives
        return self.true_positives / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.true_positives + self.false_negatives
        return self.true_positives / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _match(expected: Any, produced: Any) -> bool:
    """Exact match, with light normalisation for strings and numbers."""
    if isinstance(expected, str) and isinstance(produced, str):
        return expected.strip().casefold() == produced.strip().casefold()
    if isinstance(expected, (int, float)) and isinstance(produced, (int, float)):
        return abs(float(expected) - float(produced)) < 1e-9
    return bool(expected == produced)


def score_field(
    field_name: str, cases: list[GoldenCase], predictions: dict[str, Prediction]
) -> FieldScore:
    tp = fp = fn = 0
    for case in cases:
        if field_name not in case.expected:
            continue
        expected = case.expected[field_name]
        pred = predictions.get(case.case_id)
        produced = pred.produced.get(field_name) if pred else None

        if produced is None:
            fn += 1                      # we should have found it and did not
        elif _match(expected, produced):
            tp += 1
        else:
            fp += 1                      # wrong value asserted — worse than silence
            fn += 1
    return FieldScore(field_name, tp, fp, fn)


@dataclass(frozen=True, slots=True)
class EvalReport:
    product: str
    version: str
    case_count: int
    fields: dict[str, FieldScore]
    calibration: dict[str, float]

    @property
    def macro_f1(self) -> float:
        """Unweighted mean across fields — every field counts equally, so a
        rare-but-critical field cannot be drowned out by a common easy one."""
        if not self.fields:
            return 0.0
        return sum(f.f1 for f in self.fields.values()) / len(self.fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "version": self.version,
            "cases": self.case_count,
            "macro_f1": round(self.macro_f1, 4),
            "fields": {
                name: {
                    "precision": round(s.precision, 4),
                    "recall": round(s.recall, 4),
                    "f1": round(s.f1, 4),
                    "tp": s.true_positives,
                    "fp": s.false_positives,
                    "fn": s.false_negatives,
                }
                for name, s in sorted(self.fields.items())
            },
            "calibration": {k: round(v, 4) for k, v in sorted(self.calibration.items())},
        }


def _calibration(
    cases: list[GoldenCase], predictions: dict[str, Prediction]
) -> dict[str, float]:
    """Bucket predictions by stated confidence, report observed accuracy.

    A well-calibrated system is right ~75% of the time in the 0.7–0.8 bucket.
    Large gaps mean the confidence number is decorative, and the escalation
    boundary that depends on it is unsafe.
    """
    buckets: dict[str, list[bool]] = {}
    for case in cases:
        pred = predictions.get(case.case_id)
        if not pred:
            continue
        for name, expected in case.expected.items():
            conf = pred.confidence.get(name)
            if conf is None:
                continue
            lo = min(int(conf * 10) / 10, 0.9)
            key = f"{lo:.1f}-{lo + 0.1:.1f}"
            buckets.setdefault(key, []).append(_match(expected, pred.produced.get(name)))
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


def evaluate(
    product: str,
    version: str,
    cases: list[GoldenCase],
    predictions: list[Prediction],
) -> EvalReport:
    by_id = {p.case_id: p for p in predictions}
    names = sorted({f for c in cases for f in c.expected})
    return EvalReport(
        product=product,
        version=version,
        case_count=len(cases),
        fields={n: score_field(n, cases, by_id) for n in names},
        calibration=_calibration(cases, by_id),
    )


def load_golden_set(directory: Path) -> list[GoldenCase]:
    """Read every ``*.json`` case in a product's ``evals/golden`` directory."""
    cases: list[GoldenCase] = []
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text())
        cases.append(
            GoldenCase(
                case_id=raw.get("case_id", path.stem),
                inputs=raw["inputs"],
                expected=raw["expected"],
                notes=raw.get("notes", ""),
            )
        )
    return cases


def assert_no_regression(
    current: EvalReport, baseline: dict[str, Any], threshold: float = 0.02
) -> None:
    """Raise if macro F1, or any single field's F1, fell by more than ``threshold``."""
    base_macro = float(baseline.get("macro_f1", 0.0))
    drop = base_macro - current.macro_f1
    if drop > threshold:
        raise RegressionError(
            f"macro F1 fell {drop:.4f} (baseline {base_macro:.4f} → {current.macro_f1:.4f}), "
            f"threshold {threshold:.4f}"
        )
    for name, score in current.fields.items():
        base_f1 = float(baseline.get("fields", {}).get(name, {}).get("f1", 0.0))
        field_drop = base_f1 - score.f1
        if field_drop > threshold:
            raise RegressionError(
                f"field {name!r} F1 fell {field_drop:.4f} "
                f"(baseline {base_f1:.4f} → {score.f1:.4f}), threshold {threshold:.4f}"
            )
