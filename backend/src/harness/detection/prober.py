from harness.adapters.http_agent import HTTPAgentAdapter
from harness.adapters.types import AgentResponse, RunContext, TokenUsage, Turn
from harness.detection.classifier import classify_capabilities

PROBE_MESSAGES = [
    "What can you help me with? What are your capabilities?",
    "What is 15 * 23 + 7?",
    "Based on your knowledge base, what information do you have available?",
]


async def probe_agent(
    endpoint_url: str,
    auth_header: str | None = None,
    schema_type: str = "openai",
) -> tuple[set[str], list[AgentResponse]]:
    adapter = HTTPAgentAdapter(
        endpoint_url=endpoint_url,
        auth_header=auth_header,
        schema_type=schema_type,
        detected_capabilities={"text"},
    )
    ctx = RunContext(run_id="probe", suite_id="probe", timeout_s=30.0)
    responses: list[AgentResponse] = []
    for msg in PROBE_MESSAGES:
        try:
            resp = await adapter.invoke([Turn(role="user", content=msg)], ctx)
            responses.append(resp)
        except Exception:
            responses.append(
                AgentResponse(
                    output="",
                    tool_calls=[],
                    retrieved_contexts=[],
                    latency_ms=0,
                    token_usage=TokenUsage(input_tokens=0, output_tokens=0),
                    raw_events=[],
                )
            )
    return classify_capabilities(responses), responses
