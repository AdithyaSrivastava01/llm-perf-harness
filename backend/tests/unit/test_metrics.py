from harness.adapters.types import ToolCall
from harness.eval.metrics import MetricBackend, MetricConfig, route_metrics, _tool_trajectory_score, _rouge1_score


def test_metric_config_creation() -> None:
    config = MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0, params={"match_type": "EXACT"})
    assert config.backend == MetricBackend.ADK


def test_route_metrics_filters_by_supported() -> None:
    all_configs = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
        MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
        MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
    ]
    routed = route_metrics(all_configs, ["tool_trajectory_avg_score", "answer_relevancy"])
    assert len(routed) == 2
    assert "faithfulness" not in [m.name for m in routed]


def test_tool_trajectory_exact_match() -> None:
    assert _tool_trajectory_score([ToolCall(name="get_weather", args={})], [ToolCall(name="get_weather", args={})]) == 1.0


def test_tool_trajectory_wrong_tool() -> None:
    assert _tool_trajectory_score([ToolCall(name="calculate", args={})], [ToolCall(name="get_weather", args={})]) == 0.0


def test_tool_trajectory_partial() -> None:
    actual = [ToolCall(name="get_weather", args={}), ToolCall(name="search", args={})]
    expected = [ToolCall(name="get_weather", args={}), ToolCall(name="calculate", args={})]
    assert _tool_trajectory_score(actual, expected) == 0.5


def test_tool_trajectory_empty() -> None:
    assert _tool_trajectory_score([], []) == 1.0
    assert _tool_trajectory_score([ToolCall(name="x", args={})], []) == 0.0


def test_rouge1_exact() -> None:
    assert _rouge1_score("hello world", "hello world") == 1.0


def test_rouge1_partial() -> None:
    assert 0.0 < _rouge1_score("hello world foo", "hello world bar") < 1.0


def test_rouge1_no_overlap() -> None:
    assert _rouge1_score("abc def", "xyz uvw") == 0.0


def test_rouge1_empty() -> None:
    assert _rouge1_score("", "hello") == 0.0
    assert _rouge1_score("hello", "") == 0.0
