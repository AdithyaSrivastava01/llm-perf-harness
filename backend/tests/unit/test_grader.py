import pytest

from harness.eval.grader import GradeResult, calculate_grade


def test_grade_a() -> None:
    result = calculate_grade({"metric_a": 0.95, "metric_b": 0.92})
    assert result.letter == "A"
    assert result.score >= 0.9


def test_grade_b() -> None:
    result = calculate_grade({"metric_a": 0.85, "metric_b": 0.82})
    assert result.letter == "B"
    assert 0.8 <= result.score < 0.9


def test_grade_c() -> None:
    result = calculate_grade({"metric_a": 0.75, "metric_b": 0.72})
    assert result.letter == "C"
    assert 0.7 <= result.score < 0.8


def test_grade_d() -> None:
    result = calculate_grade({"metric_a": 0.65, "metric_b": 0.62})
    assert result.letter == "D"
    assert 0.6 <= result.score < 0.7


def test_grade_f() -> None:
    result = calculate_grade({"metric_a": 0.4, "metric_b": 0.3})
    assert result.letter == "F"
    assert result.score < 0.6


def test_empty_metrics_returns_f() -> None:
    result = calculate_grade({})
    assert result.letter == "F"
    assert result.score == 0.0


def test_single_metric_perfect() -> None:
    result = calculate_grade({"only_metric": 1.0})
    assert result.letter == "A"
    assert result.score == 1.0


def test_grade_result_is_frozen() -> None:
    result = GradeResult(letter="A", score=0.95)
    with pytest.raises((AttributeError, TypeError)):
        result.letter = "B"  # type: ignore[misc]


def test_score_rounded() -> None:
    result = calculate_grade({"m": 0.833333333})
    # score should be rounded to 4 decimal places
    assert result.score == round(0.833333333, 4)
