import pytest
from bai_platform.evals import (
    GoldenCase,
    Prediction,
    RegressionError,
    assert_no_regression,
    evaluate,
    score_field,
)


def case(cid: str, **expected: object) -> GoldenCase:
    return GoldenCase(case_id=cid, inputs={}, expected=expected)


class TestFieldScoring:
    def test_perfect_extraction(self) -> None:
        cases = [case("1", total=100), case("2", total=200)]
        preds = {"1": Prediction("1", {"total": 100}), "2": Prediction("2", {"total": 200})}
        s = score_field("total", cases, preds)
        assert (s.precision, s.recall, s.f1) == (1.0, 1.0, 1.0)

    def test_a_wrong_value_is_worse_than_silence(self) -> None:
        """A wrong assertion costs both precision and recall; a miss costs recall
        only. That asymmetry is deliberate — confidently wrong is the worse failure."""
        cases = [case("1", total=100)]
        wrong = score_field("total", cases, {"1": Prediction("1", {"total": 999})})
        silent = score_field("total", cases, {"1": Prediction("1", {})})
        assert wrong.false_positives == 1 and wrong.false_negatives == 1
        assert silent.false_positives == 0 and silent.false_negatives == 1

    def test_string_matching_is_normalised(self) -> None:
        cases = [case("1", name="Acme Ltd")]
        s = score_field("name", cases, {"1": Prediction("1", {"name": "  acme ltd  "})})
        assert s.f1 == 1.0


class TestRegressionGate:
    def _report(self, f1_case_count: int, correct: int):
        cases = [case(str(i), total=i) for i in range(f1_case_count)]
        preds = [
            Prediction(str(i), {"total": i if i < correct else -1}, {"total": 0.9})
            for i in range(f1_case_count)
        ]
        return evaluate("demo", "v1", cases, preds)

    def test_passes_within_threshold(self) -> None:
        current = self._report(10, 10)
        assert_no_regression(current, {"macro_f1": 1.0, "fields": {"total": {"f1": 1.0}}}, 0.02)

    def test_blocks_on_regression(self) -> None:
        current = self._report(10, 5)
        with pytest.raises(RegressionError, match="macro F1 fell"):
            assert_no_regression(current, {"macro_f1": 1.0, "fields": {"total": {"f1": 1.0}}}, 0.02)

    def test_blocks_when_one_field_collapses(self) -> None:
        """An aggregate can hide the field that matters most, so each is gated."""
        cases = [case(str(i), a=i, b=i) for i in range(10)]
        preds = [Prediction(str(i), {"a": i, "b": -1}) for i in range(10)]
        current = evaluate("demo", "v1", cases, preds)
        baseline = {"macro_f1": 0.5, "fields": {"a": {"f1": 1.0}, "b": {"f1": 1.0}}}
        with pytest.raises(RegressionError, match="field 'b'"):
            assert_no_regression(current, baseline, 0.02)


class TestCalibration:
    def test_reports_observed_accuracy_per_bucket(self) -> None:
        """When the system says 80%, is it right 80% of the time? A miscalibrated
        score makes the escalation boundary unsafe."""
        cases = [case(str(i), total=i) for i in range(4)]
        preds = [
            Prediction("0", {"total": 0}, {"total": 0.85}),
            Prediction("1", {"total": 1}, {"total": 0.85}),
            Prediction("2", {"total": -1}, {"total": 0.85}),
            Prediction("3", {"total": -1}, {"total": 0.85}),
        ]
        report = evaluate("demo", "v1", cases, preds)
        assert report.calibration["0.8-0.9"] == 0.5

