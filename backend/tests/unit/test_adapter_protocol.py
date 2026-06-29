import pytest

from harness.adapters.protocol import AgentAdapter
from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn


class MockToolCallingAdapter:
    @property
    def agent_id(self) -> str:
        return "mock-tool-agent"

    @property
    def display_name(self) -> str:
        return "Mock Tool Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        return AgentResponse(
            output="Sunny in Paris",
            tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
            retrieved_contexts=[],
            latency_ms=100.0,
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
            raw_events=[],
        )

    def supported_metrics(self) -> list[str]:
        return ["tool_trajectory_avg_score", "answer_relevancy"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [ToolSpec(name="get_weather", description="Get weather", parameters={"city": "string"})]

    def reference_contexts(self) -> list[str] | None:
        return None


class IncompleteAdapter:
    @property
    def agent_id(self) -> str:
        return "incomplete"


def test_mock_adapter_satisfies_protocol() -> None:
    adapter: AgentAdapter = MockToolCallingAdapter()
    assert adapter.agent_id == "mock-tool-agent"
    assert "tools" in adapter.capabilities
    assert adapter.expected_tools() is not None
    assert adapter.reference_contexts() is None


@pytest.mark.asyncio
async def test_mock_adapter_invoke() -> None:
    adapter = MockToolCallingAdapter()
    ctx = RunContext(run_id="run-1", suite_id="suite-1")
    response = await adapter.invoke([Turn(role="user", content="Weather in Paris?")], ctx)
    assert response.output == "Sunny in Paris"
    assert len(response.tool_calls) == 1


def test_incomplete_adapter_not_protocol() -> None:
    adapter = IncompleteAdapter()
    assert not isinstance(adapter, AgentAdapter)
