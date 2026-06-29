import pytest

from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.eval.metrics import MetricBackend, MetricConfig


class StubAdapter:
    @property
    def agent_id(self) -> str:
        return "stub"

    @property
    def display_name(self) -> str:
        return "Stub"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        return AgentResponse(
            output="Sunny in Paris",
            tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
            retrieved_contexts=[],
            latency_ms=50.0,
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
            raw_events=[],
        )

    def supported_metrics(self) -> list[str]:
        return ["tool_trajectory_avg_score"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [ToolSpec(name="get_weather", description="", parameters={})]

    def reference_contexts(self) -> list[str] | None:
        return None


@pytest.mark.asyncio
async def test_eval_runner_produces_report() -> None:
    adapter = StubAdapter()
    metrics = [MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0)]
    test_cases = [
        EvalTestCase(
            id="tc-1",
            input=[Turn(role="user", content="Weather in Paris?")],
            expected_output="Sunny in Paris",
            expected_tools=[ToolCall(name="get_weather", args={"city": "Paris"})],
            reference_contexts=None,
            tags=["weather"],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id="run-1", suite_id="suite-1")

    assert report.run_id == "run-1"
    assert len(report.case_results) == 1
    assert report.case_results[0].passed is True
    assert report.overall_passed is True


@pytest.mark.asyncio
async def test_eval_runner_with_failing_case() -> None:
    adapter = StubAdapter()
    metrics = [MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0)]
    test_cases = [
        EvalTestCase(
            id="tc-1",
            input=[Turn(role="user", content="Weather?")],
            expected_output=None,
            expected_tools=[ToolCall(name="calculate", args={"expression": "1+1"})],
            reference_contexts=None,
            tags=[],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id="run-2", suite_id="suite-1")

    assert report.case_results[0].passed is False
    assert report.overall_passed is False


@pytest.mark.asyncio
async def test_eval_runner_filters_unsupported_metrics() -> None:
    adapter = StubAdapter()
    metrics = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
        MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
    ]
    test_cases = [
        EvalTestCase(
            id="tc-1",
            input=[Turn(role="user", content="Weather?")],
            expected_output=None,
            expected_tools=[ToolCall(name="get_weather", args={})],
            reference_contexts=None,
            tags=[],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id="run-3", suite_id="suite-1")

    # Only tool_trajectory should be scored, faithfulness filtered out
    assert len(report.case_results[0].metric_results) == 1
    assert report.case_results[0].metric_results[0].name == "tool_trajectory_avg_score"
