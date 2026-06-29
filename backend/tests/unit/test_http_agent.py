from harness.adapters.http_agent import HTTPAgentAdapter, parse_openai_response
from harness.adapters.types import ToolCall


def test_parse_openai_response_text_only() -> None:
    raw = {
        "choices": [{"message": {"content": "Hello!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    output, tool_calls, usage = parse_openai_response(raw)
    assert output == "Hello!" and tool_calls == [] and usage.input_tokens == 10


def test_parse_openai_response_with_tool_calls() -> None:
    raw = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city":"Paris"}',
                            },
                            "type": "function",
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 8},
    }
    output, tool_calls, usage = parse_openai_response(raw)
    assert output == "" and len(tool_calls) == 1 and tool_calls[0].name == "get_weather"


def test_parse_missing_usage() -> None:
    output, _, usage = parse_openai_response(
        {"choices": [{"message": {"content": "Hi"}}]}
    )
    assert output == "Hi" and usage.input_tokens == 0


def test_http_adapter_metadata() -> None:
    a = HTTPAgentAdapter(
        endpoint_url="https://example.com/v1/chat/completions",
        detected_capabilities={"text", "tools"},
    )
    assert a.agent_id.startswith("http-") and a.capabilities == {"text", "tools"}


def test_supported_metrics_text_only() -> None:
    a = HTTPAgentAdapter(endpoint_url="x", detected_capabilities={"text"})
    assert (
        "answer_relevancy" in a.supported_metrics()
        and "faithfulness" not in a.supported_metrics()
    )


def test_supported_metrics_rag() -> None:
    a = HTTPAgentAdapter(endpoint_url="x", detected_capabilities={"text", "rag"})
    m = a.supported_metrics()
    assert "faithfulness" in m and "hallucination" in m
