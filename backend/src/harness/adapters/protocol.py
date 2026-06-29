from typing import Protocol, runtime_checkable

from harness.adapters.types import AgentResponse, RunContext, ToolSpec, Turn


@runtime_checkable
class AgentAdapter(Protocol):

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def capabilities(self) -> set[str]: ...

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse: ...

    def supported_metrics(self) -> list[str]: ...

    def expected_tools(self) -> list[ToolSpec] | None: ...

    def reference_contexts(self) -> list[str] | None: ...
