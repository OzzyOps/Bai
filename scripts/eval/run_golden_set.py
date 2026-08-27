#!/usr/bin/env python3
"""Run every product's golden set and gate on regression.

BAi sells correctness. Correctness that is not measured is a claim, not a
product — so this is a merge gate, not a report.

  --all                 run every product under products/
  --report FILE         write the JSON report
  --check-regression    compare against each product's baseline
  --threshold F         maximum permitted F1 drop (default 0.02)
  --calibration         print the confidence calibration table
  --update-baseline     rewrite baselines (deliberate, never automatic in CI)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/platform-py/src"))

from bai_platform.evals import (
    EvalReport,
    Prediction,
    RegressionError,
    assert_no_regression,
    evaluate,
    load_golden_set,
)

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS = ROOT / "products"


def predict(product: str, cases: list) -> list[Prediction]:
    """Hook for the product's agent.

    Each product registers a runner in ``products/<name>/evals/runner.py``. Until
    one exists we fail loudly rather than reporting a fabricated score — a green
    tick from a stubbed predictor is worse than no tick.
    """
    runner = PRODUCTS / product / "evals" / "runner.py"
    if not runner.exists():
        raise SystemExit(
            f"✖ {product} has a golden set but no evals/runner.py.\n"
            f"  Cannot score without a predictor. No golden set, no ship."
        )
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"{product}_runner", runner)
    if spec is None or spec.loader is None:
        raise SystemExit(f"✖ could not load {runner}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.predict(cases))


def run_product(product_dir: Path, *, threshold: float, check: bool) -> tuple[EvalReport, bool]:
    golden = product_dir / "evals" / "golden"
    cases = load_golden_set(golden)
    if not cases:
        raise SystemExit(f"✖ {product_dir.name}: golden set at {golden} is empty")

    report = evaluate(product_dir.name, "HEAD", cases, predict(product_dir.name, cases))
    ok = True

    if check:
        baseline_path = product_dir / "evals" / "baseline.json"
        if not baseline_path.exists():
            print(f"  ⚠ no baseline for {product_dir.name}; recording this run as the baseline")
            baseline_path.write_text(json.dumps(report.to_dict(), indent=2))
        else:
            try:
                assert_no_regression(report, json.loads(baseline_path.read_text()), threshold)
                print(f"  ✓ {product_dir.name}: no regression beyond {threshold:.0%}")
            except RegressionError as exc:
                print(f"  ✖ {product_dir.name}: {exc}")
                ok = False
    return report, ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--all", action="store_true")
    p.add_argument("--product")
    p.add_argument("--report", type=Path)
    p.add_argument("--check-regression", action="store_true")
    p.add_argument("--threshold", type=float, default=0.02)
    p.add_argument("--calibration", action="store_true")
    p.add_argument("--update-baseline", action="store_true")
    args = p.parse_args()

    if not PRODUCTS.exists():
        print("No products/ directory yet — nothing to evaluate.")
        return 0

    targets = (
        [d for d in sorted(PRODUCTS.iterdir()) if (d / "evals" / "golden").is_dir()]
        if args.all
        else [PRODUCTS / args.product] if args.product
        else []
    )
    if not targets:
        print("No products with a golden set. Nothing to evaluate.")
        return 0

    reports: dict[str, dict] = {}
    all_ok = True

    for target in targets:
        print(f"▶ {target.name}")
        report, ok = run_product(
            target, threshold=args.threshold, check=args.check_regression
        )
        all_ok &= ok
        reports[target.name] = report.to_dict()

        print(f"  macro F1 {report.macro_f1:.4f} over {report.case_count} cases")
        for name, score in sorted(report.fields.items()):
            print(f"    {name:<28} P {score.precision:.3f}  R {score.recall:.3f}  F1 {score.f1:.3f}")

        if args.calibration and report.calibration:
            print("  confidence calibration (stated → observed):")
            for bucket, observed in sorted(report.calibration.items()):
                print(f"    {bucket:<10} {observed:.3f}")

        if args.update_baseline:
            (target / "evals" / "baseline.json").write_text(
                json.dumps(report.to_dict(), indent=2)
            )
            print("  baseline updated")

    if args.report:
        args.report.write_text(json.dumps(reports, indent=2))
        print(f"\n✓ report written to {args.report}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
