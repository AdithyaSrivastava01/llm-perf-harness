from harness.adapters.types import AgentResponse, TokenUsage, ToolCall
from harness.detection.classifier import classify_capabilities


def _make_response(
    output: str = "",
    tool_calls: list[ToolCall] | None = None,
    retrieved_contexts: list[str] | None = None,
) -> AgentResponse:
    return AgentResponse(
        output=output,
        tool_calls=tool_calls or [],
        retrieved_contexts=retrieved_contexts or [],
        latency_ms=100.0,
        token_usage=TokenUsage(input_tokens=10, output_tokens=20),
        raw_events=[],
    )


def test_empty_responses_returns_text_only() -> None:
    caps = classify_capabilities([])
    assert caps == {"text"}


def test_text_only_responses() -> None:
    responses = [_make_response(output="Hello, I can help you.")]
    caps = classify_capabilities(responses)
    assert caps == {"text"}


def test_tool_calls_adds_tools_capability() -> None:
    responses = [
        _make_response(
            tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})]
        )
    ]
    caps = classify_capabilities(responses)
    assert "tools" in caps
    assert "text" in caps


def test_retrieved_contexts_adds_rag_capability() -> None:
    responses = [_make_response(retrieved_contexts=["doc1 content", "doc2 content"])]
    caps = classify_capabilities(responses)
    assert "rag" in caps
    assert "text" in caps


def test_all_capabilities_detected() -> None:
    responses = [
        _make_response(
            output="Here is the answer.",
            tool_calls=[ToolCall(name="search", args={"query": "test"})],
            retrieved_contexts=["context chunk"],
        )
    ]
    caps = classify_capabilities(responses)
    assert caps == {"text", "tools", "rag"}


def test_mixed_responses() -> None:
    responses = [
        _make_response(output="plain text"),
        _make_response(tool_calls=[ToolCall(name="calculate", args={"expr": "1+1"})]),
    ]
    caps = classify_capabilities(responses)
    assert "text" in caps
    assert "tools" in caps
    assert "rag" not in caps


def test_always_returns_set() -> None:
    caps = classify_capabilities([_make_response()])
    assert isinstance(caps, set)
