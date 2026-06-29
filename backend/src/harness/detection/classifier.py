from harness.adapters.types import AgentResponse

RAG_KEYWORDS = [
    "document",
    "retrieved",
    "source",
    "knowledge base",
    "context",
    "based on",
    "according to",
    "reference",
    "search result",
]


def classify_capabilities(probe_responses: list[AgentResponse]) -> set[str]:
    caps: set[str] = {"text"}
    for resp in probe_responses:
        if resp.tool_calls:
            caps.add("tools")
        output_lower = resp.output.lower()
        if any(kw in output_lower for kw in RAG_KEYWORDS):
            caps.add("rag")
    return caps
