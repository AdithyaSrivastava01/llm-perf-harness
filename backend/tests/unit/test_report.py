from harness.adapters.types import MetricResult
from harness.eval.report import CaseResult, EvalReport


def test_case_result_passed_all_pass() -> None:
    case = CaseResult(test_case_id="tc-1", metric_results=[
        MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk"),
        MetricResult(name="m2", score=0.9, threshold=0.8, details={}, backend="deepeval"),
    ], latency_ms=100.0)
    assert case.passed is True


def test_case_result_fails_any_fail() -> None:
    case = CaseResult(test_case_id="tc-1", metric_results=[
        MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk"),
        MetricResult(name="m2", score=0.5, threshold=0.8, details={}, backend="deepeval"),
    ], latency_ms=100.0)
    assert case.passed is False


def test_eval_report_summary() -> None:
    report = EvalReport(run_id="run-1", suite_id="suite-1", case_results=[
        CaseResult(test_case_id="tc-1", metric_results=[
            MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk")
        ], latency_ms=100.0),
        CaseResult(test_case_id="tc-2", metric_results=[
            MetricResult(name="m1", score=0.5, threshold=0.8, details={}, backend="adk")
        ], latency_ms=200.0),
    ])
    s = report.summary()
    assert s["total_cases"] == 2 and s["passed"] == 1 and s["failed"] == 1
    assert s["pass_rate"] == 0.5 and s["avg_latency_ms"] == 150.0


def test_eval_report_overall_passed() -> None:
    report = EvalReport(run_id="r", suite_id="s", case_results=[
        CaseResult(test_case_id="tc-1", metric_results=[
            MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk")
        ], latency_ms=100.0),
    ])
    assert report.overall_passed is True


def test_eval_report_metric_averages() -> None:
    report = EvalReport(run_id="r", suite_id="s", case_results=[
        CaseResult(test_case_id="tc-1", metric_results=[
            MetricResult(name="a", score=0.8, threshold=0.5, details={}, backend="adk"),
            MetricResult(name="b", score=0.6, threshold=0.5, details={}, backend="adk"),
        ], latency_ms=100.0),
        CaseResult(test_case_id="tc-2", metric_results=[
            MetricResult(name="a", score=1.0, threshold=0.5, details={}, backend="adk"),
            MetricResult(name="b", score=0.4, threshold=0.5, details={}, backend="adk"),
        ], latency_ms=200.0),
    ])
    s = report.summary()
    assert s["metric_averages"]["a"] == 0.9 and s["metric_averages"]["b"] == 0.5
