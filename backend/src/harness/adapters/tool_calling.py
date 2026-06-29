import time
from typing import Any

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from harness.adapters.types import (
    AgentResponse,
    RunContext,
    TokenUsage,
    ToolCall,
    ToolSpec,
    Turn,
)
from harness.agents.tool_calling_agent import create_tool_calling_agent


class ToolCallingAdapter:
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._agent = create_tool_calling_agent(model)
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            session_service=self._session_service,
            app_name="tool_calling_eval",
        )

    @property
    def agent_id(self) -> str:
        return "tool-calling-agent"

    @property
    def display_name(self) -> str:
        return "Tool-Calling Demo Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        session = await self._session_service.create_session(
            app_name="tool_calling_eval", user_id=f"eval-{context.run_id}"
        )
        tool_calls: list[ToolCall] = []
        final_output = ""
        raw_events: list[Any] = []
        input_tokens = 0
        output_tokens = 0
        start = time.monotonic()

        for turn in input:
            message = Content(role=turn.role, parts=[Part(text=turn.content)])
            async for event in self._runner.run_async(
                user_id=f"eval-{context.run_id}",
                session_id=session.id,
                new_message=message,
            ):
                raw_events.append(event)
                if event.actions and event.actions.function_calls:
                    for fc in event.actions.function_calls:
                        tool_calls.append(
                            ToolCall(name=fc.name, args=dict(fc.args or {}))
                        )
                if event.is_final_response() and event.content and event.content.parts:
                    final_output = event.content.parts[0].text or ""
                if hasattr(event, "usage") and event.usage:
                    input_tokens += getattr(event.usage, "prompt_tokens", 0)
                    output_tokens += getattr(event.usage, "completion_tokens", 0)

        elapsed = (time.monotonic() - start) * 1000
        return AgentResponse(
            output=final_output,
            tool_calls=tool_calls,
            retrieved_contexts=[],
            latency_ms=elapsed,
            token_usage=TokenUsage(
                input_tokens=input_tokens, output_tokens=output_tokens
            ),
            raw_events=raw_events,
        )

    def supported_metrics(self) -> list[str]:
        return [
            "tool_trajectory_avg_score",
            "final_response_match_v2",
            "answer_relevancy",
        ]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [
            ToolSpec(
                name="get_weather",
                description="Get weather for a city",
                parameters={"city": "string"},
            ),
            ToolSpec(
                name="calculate",
                description="Evaluate math expression",
                parameters={"expression": "string"},
            ),
            ToolSpec(
                name="search_knowledge",
                description="Search knowledge base",
                parameters={"query": "string"},
            ),
        ]

    def reference_contexts(self) -> list[str] | None:
        return None
