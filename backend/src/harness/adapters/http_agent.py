import time
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


class HTTPAgentAdapter:
    """Adapter for communicating with external HTTP-based agent endpoints."""

    def __init__(
        self,
        endpoint_url: str,
        auth_header: str | None = None,
        schema_type: str = "openai",
        detected_capabilities: set[str] | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._auth_header = auth_header
        self._schema_type = schema_type
        self._capabilities = detected_capabilities or {"text"}

    @property
    def agent_id(self) -> str:
        return f"http-agent-{self._endpoint_url}"

    @property
    def display_name(self) -> str:
        return f"HTTP Agent ({self._endpoint_url})"

    @property
    def capabilities(self) -> set[str]:
        return self._capabilities

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        payload = self._build_payload(input)
        start = time.monotonic()

        async with httpx.AsyncClient(timeout=context.timeout_s) as client:
            response = await client.post(
                self._endpoint_url, json=payload, headers=headers
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        elapsed = (time.monotonic() - start) * 1000
        return self._parse_response(data, elapsed)

    def _build_payload(self, input: list[Turn]) -> dict[str, Any]:
        if self._schema_type == "openai":
            return {"messages": [{"role": t.role, "content": t.content} for t in input]}
        # Generic fallback
        return {
            "input": input[-1].content if input else "",
            "history": [{"role": t.role, "content": t.content} for t in input[:-1]],
        }

    def _parse_response(self, data: dict[str, Any], elapsed: float) -> AgentResponse:
        output = ""
        tool_calls: list[ToolCall] = []
        input_tokens = 0
        output_tokens = 0

        # OpenAI-compatible response format
        if "choices" in data:
            choice = data["choices"][0] if data["choices"] else {}
            message = choice.get("message", {})
            output = message.get("content") or ""
            # Parse tool_calls if present
            for tc in message.get("tool_calls", []):
                fn = tc.get("function", {})
                import json

                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(ToolCall(name=fn.get("name", ""), args=args))
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
        elif "output" in data:
            output = data["output"]
        elif "response" in data:
            output = data["response"]
        elif "text" in data:
            output = data["text"]
        elif "content" in data:
            output = data["content"]

        return AgentResponse(
            output=output,
            tool_calls=tool_calls,
            retrieved_contexts=[],
            latency_ms=elapsed,
            token_usage=TokenUsage(
                input_tokens=input_tokens, output_tokens=output_tokens
            ),
            raw_events=[data],
        )

    def supported_metrics(self) -> list[str]:
        metrics = ["answer_relevancy"]
        if "tools" in self._capabilities:
            metrics += ["tool_trajectory_avg_score", "final_response_match_v2"]
        if "rag" in self._capabilities:
            metrics += ["faithfulness", "contextual_relevancy", "hallucination"]
        return metrics

    def expected_tools(self) -> list[ToolSpec] | None:
        return None

    def reference_contexts(self) -> list[str] | None:
        return None
