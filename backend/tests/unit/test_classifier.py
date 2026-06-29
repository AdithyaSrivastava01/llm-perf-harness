from harness.adapters.types import AgentResponse, TokenUsage, ToolCall
from harness.detection.classifier import classify_capabilities


def _resp(output: str, tool_calls=None) -> AgentResponse:
    return AgentResponse(
        output=output,
        tool_calls=tool_calls or [],
        retrieved_contexts=[],
        latency_ms=100,
        token_usage=TokenUsage(10, 5),
        raw_events=[],
    )


def test_classify_text_only() -> None:
    caps = classify_capabilities(
        [
            _resp("I help with questions."),
            _resp("Not sure."),
            _resp("I cannot help with that."),
        ]
    )
    assert caps == {"text"}


def test_classify_tools_from_tool_calls() -> None:
    caps = classify_capabilities(
        [_resp("Hi"), _resp("352", [ToolCall(name="calc", args={})]), _resp("No.")]
    )
    assert "tools" in caps


def test_classify_rag_from_text() -> None:
    caps = classify_capabilities(
        [
            _resp("I search documents."),
            _resp("42"),
            _resp("Based on retrieved documents, yes."),
        ]
    )
    assert "rag" in caps


def test_classify_all() -> None:
    caps = classify_capabilities(
        [
            _resp("I search."),
            _resp("352", [ToolCall(name="c", args={})]),
            _resp("According to source documents."),
        ]
    )
    assert caps == {"text", "tools", "rag"}
