import json
import uuid
from harness.meta_tools.registry import get_adapter


def generate_test_cases(agent_id: str, num_cases: int = 10, focus: str = "") -> str:
    """Generate test cases for a specific agent based on its capabilities."""
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})
    num_cases = min(num_cases, 50)
    if "rag" in adapter.capabilities:
        cases = _generate_rag_cases(num_cases)
    elif "tools" in adapter.capabilities:
        cases = _generate_tool_calling_cases(num_cases)
    else:
        cases = [
            {
                "id": f"gen-{i}",
                "input": [{"role": "user", "content": f"Test query {i}"}],
                "approved": False,
            }
            for i in range(num_cases)
        ]
    return json.dumps(
        {
            "agent_id": agent_id,
            "generated_count": len(cases),
            "cases": cases,
            "note": "Review these cases before running eval. Use review_test_cases to approve.",
        },
        indent=2,
    )


def _generate_tool_calling_cases(num_cases: int) -> list[dict]:
    templates = [
        {
            "input": "What is the weather in London?",
            "tool": "get_weather",
            "args": {"city": "London"},
        },
        {
            "input": "What is the weather in Tokyo?",
            "tool": "get_weather",
            "args": {"city": "Tokyo"},
        },
        {
            "input": "What is the weather in New York?",
            "tool": "get_weather",
            "args": {"city": "New York"},
        },
        {
            "input": "Calculate 42 * 17",
            "tool": "calculate",
            "args": {"expression": "42 * 17"},
        },
        {
            "input": "What is sqrt(144)?",
            "tool": "calculate",
            "args": {"expression": "sqrt(144)"},
        },
        {
            "input": "What is 2^10?",
            "tool": "calculate",
            "args": {"expression": "pow(2, 10)"},
        },
        {
            "input": "Tell me about machine learning",
            "tool": "search_knowledge",
            "args": {"query": "machine learning"},
        },
        {
            "input": "What is FastAPI?",
            "tool": "search_knowledge",
            "args": {"query": "FastAPI"},
        },
        {
            "input": "Search for Python programming",
            "tool": "search_knowledge",
            "args": {"query": "Python"},
        },
        {
            "input": "What is the weather in Paris?",
            "tool": "get_weather",
            "args": {"city": "Paris"},
        },
    ]
    return [
        {
            "id": f"gen-tc-{uuid.uuid4().hex[:8]}",
            "input": [{"role": "user", "content": t["input"]}],
            "expected_tools": [{"name": t["tool"], "args": t["args"]}],
            "expected_output": None,
            "tags": ["generated", t["tool"]],
            "approved": False,
        }
        for t in templates[:num_cases]
    ]


def _generate_rag_cases(num_cases: int) -> list[dict]:
    from harness.agents.rag_agent import DOCUMENTS

    cases = []
    for doc in DOCUMENTS[:num_cases]:
        title = doc["title"].replace("What is ", "").rstrip("?")
        cases.append(
            {
                "id": f"gen-rag-{uuid.uuid4().hex[:8]}",
                "input": [{"role": "user", "content": f"What is {title}?"}],
                "expected_output": None,
                "reference_contexts": [doc["content"]],
                "tags": ["generated", "rag"],
                "approved": False,
            }
        )
    return cases[:num_cases]
