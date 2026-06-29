from harness.adapters.types import AgentResponse


def classify_capabilities(responses: list[AgentResponse]) -> set[str]:
    """Infer agent capabilities from probe responses.

    Always includes "text". Adds "tools" if any tool calls were made,
    and "rag" if retrieved contexts are present.
    """
    capabilities: set[str] = {"text"}

    for resp in responses:
        if resp.tool_calls:
            capabilities.add("tools")
        if resp.retrieved_contexts:
            capabilities.add("rag")

    return capabilities
