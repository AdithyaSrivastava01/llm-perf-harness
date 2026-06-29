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
from harness.agents.rag_agent import DOCUMENTS, create_rag_agent


class RAGAdapter:
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._agent = create_rag_agent(model)
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            session_service=self._session_service,
            app_name="rag_eval",
        )

    @property
    def agent_id(self) -> str:
        return "rag-agent"

    @property
    def display_name(self) -> str:
        return "RAG Demo Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools", "rag"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        session = await self._session_service.create_session(
            app_name="rag_eval", user_id=f"eval-{context.run_id}"
        )
        tool_calls: list[ToolCall] = []
        final_output = ""
        raw_events: list[Any] = []
        retrieved_contexts: list[str] = []
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
                for fc in event.get_function_calls():
                    tool_calls.append(ToolCall(name=fc.name, args=dict(fc.args or {})))
                for fr in event.get_function_responses():
                    if fr.name == "retrieve_documents" and fr.response:
                        retrieved_contexts.append(str(fr.response))
                if event.is_final_response() and event.content and event.content.parts:
                    final_output = event.content.parts[0].text or ""

        elapsed = (time.monotonic() - start) * 1000
        return AgentResponse(
            output=final_output,
            tool_calls=tool_calls,
            retrieved_contexts=retrieved_contexts,
            latency_ms=elapsed,
            token_usage=TokenUsage(
                input_tokens=input_tokens, output_tokens=output_tokens
            ),
            raw_events=raw_events,
        )

    def supported_metrics(self) -> list[str]:
        return [
            "faithfulness",
            "contextual_relevancy",
            "hallucination",
            "answer_relevancy",
        ]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [
            ToolSpec(
                name="retrieve_documents",
                description="Search docs",
                parameters={"query": "string"},
            )
        ]

    def reference_contexts(self) -> list[str] | None:
        return [doc["content"] for doc in DOCUMENTS]
