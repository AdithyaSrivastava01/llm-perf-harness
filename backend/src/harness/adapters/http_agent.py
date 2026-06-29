import hashlib, json, time
from typing import Any
import httpx
from harness.adapters.types import (
    AgentResponse,
    RunContext,
    TokenUsage,
    ToolCall,
    ToolSpec,
    Turn,
)


def parse_openai_response(raw: dict) -> tuple[str, list[ToolCall], TokenUsage]:
    choices = raw.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}
    output = message.get("content") or ""
    tool_calls = []
    for tc in message.get("tool_calls", []):
        func = tc.get("function", {})
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(name=func.get("name", ""), args=args))
    usage_raw = raw.get("usage", {})
    usage = TokenUsage(
        input_tokens=usage_raw.get("prompt_tokens", 0),
        output_tokens=usage_raw.get("completion_tokens", 0),
    )
    return output, tool_calls, usage


class HTTPAgentAdapter:
    def __init__(
        self,
        endpoint_url: str,
        auth_header: str | None = None,
        schema_type: str = "openai",
        custom_schema: dict | None = None,
        detected_capabilities: set[str] | None = None,
        display_name: str | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._auth_header = auth_header
        self._schema_type = schema_type
        self._custom_schema = custom_schema
        self._capabilities = detected_capabilities or {"text"}
        self._display_name = display_name

    @property
    def agent_id(self) -> str:
        return f"http-{hashlib.sha256(self._endpoint_url.encode()).hexdigest()[:12]}"

    @property
    def display_name(self) -> str:
        return self._display_name or self._endpoint_url

    @property
    def capabilities(self) -> set[str]:
        return self._capabilities

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        messages = [{"role": t.role, "content": t.content} for t in input]
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=context.timeout_s) as client:
            resp = await client.post(
                self._endpoint_url,
                json={"messages": messages, "temperature": 0},
                headers=headers,
            )
            resp.raise_for_status()
            raw = resp.json()
        elapsed = (time.monotonic() - start) * 1000
        output, tool_calls, usage = parse_openai_response(raw)
        return AgentResponse(
            output=output,
            tool_calls=tool_calls,
            retrieved_contexts=[],
            latency_ms=elapsed,
            token_usage=usage,
            raw_events=[raw],
        )

    def supported_metrics(self) -> list[str]:
        metrics = [
            "answer_relevancy",
            "response_match_score",
            "final_response_match_v2",
        ]
        if "tools" in self._capabilities:
            metrics.append("tool_trajectory_avg_score")
        if "rag" in self._capabilities:
            metrics.extend(["faithfulness", "contextual_relevancy", "hallucination"])
        return metrics

    def expected_tools(self) -> list[ToolSpec] | None:
        return None

    def reference_contexts(self) -> list[str] | None:
        return None
