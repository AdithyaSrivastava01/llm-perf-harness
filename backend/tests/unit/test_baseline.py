from harness.eval.baseline import BaselineSnapshot, compare_to_baseline


def test_no_regression_when_scores_improve() -> None:
    baseline = BaselineSnapshot(
        scores={"tool_trajectory_avg_score": 0.9, "answer_relevancy": 0.8},
        thresholds={"tool_trajectory_avg_score": 0.8, "answer_relevancy": 0.7},
    )
    current = {"tool_trajectory_avg_score": 1.0, "answer_relevancy": 0.85}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False
    assert len(result.regressions) == 0


def test_regression_when_score_drops_below_floor() -> None:
    baseline = BaselineSnapshot(scores={"faithfulness": 0.9}, thresholds={"faithfulness": 0.8})
    current = {"faithfulness": 0.7}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is True
    assert "faithfulness" in [r.metric_name for r in result.regressions]


def test_regression_when_score_drops_by_tolerance() -> None:
    baseline = BaselineSnapshot(
        scores={"answer_relevancy": 0.9}, thresholds={"answer_relevancy": 0.7}, tolerance=0.05,
    )
    current = {"answer_relevancy": 0.84}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is True


def test_no_regression_within_tolerance() -> None:
    baseline = BaselineSnapshot(
        scores={"answer_relevancy": 0.9}, thresholds={"answer_relevancy": 0.7}, tolerance=0.05,
    )
    current = {"answer_relevancy": 0.86}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False


def test_new_metrics_not_in_baseline_ignored() -> None:
    baseline = BaselineSnapshot(scores={"faithfulness": 0.9}, thresholds={"faithfulness": 0.8})
    current = {"faithfulness": 0.95, "new_metric": 0.7}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False
