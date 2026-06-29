from harness.adapters.types import AgentResponse, MetricResult, ToolCall, ToolSpec, TokenUsage, Turn


def test_turn_creation() -> None:
    turn = Turn(role="user", content="What is the weather?")
    assert turn.role == "user"
    assert turn.content == "What is the weather?"


def test_tool_call_creation() -> None:
    tc = ToolCall(name="get_weather", args={"city": "Paris"})
    assert tc.name == "get_weather"
    assert tc.args == {"city": "Paris"}


def test_tool_spec_creation() -> None:
    spec = ToolSpec(name="get_weather", description="Get weather", parameters={"city": "string"})
    assert spec.name == "get_weather"


def test_token_usage() -> None:
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.total_tokens == 150


def test_agent_response_creation() -> None:
    resp = AgentResponse(
        output="It's sunny in Paris",
        tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
        retrieved_contexts=[],
        latency_ms=150.5,
        token_usage=TokenUsage(input_tokens=100, output_tokens=50),
        raw_events=[],
    )
    assert resp.output == "It's sunny in Paris"
    assert len(resp.tool_calls) == 1
    assert resp.latency_ms == 150.5


def test_metric_result_passes_at_threshold() -> None:
    result = MetricResult(
        name="tool_trajectory_avg_score",
        score=1.0,
        threshold=1.0,
        details={"match_type": "EXACT"},
        backend="adk",
    )
    assert result.passed is True


def test_metric_result_fails_below_threshold() -> None:
    result = MetricResult(
        name="faithfulness",
        score=0.6,
        threshold=0.8,
        details={},
        backend="deepeval",
    )
    assert result.passed is False
