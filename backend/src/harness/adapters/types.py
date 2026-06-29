from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AgentResponse:
    output: str
    tool_calls: list[ToolCall]
    retrieved_contexts: list[str]
    latency_ms: float
    token_usage: TokenUsage
    raw_events: list[Any]


@dataclass(frozen=True)
class MetricResult:
    name: str
    score: float
    threshold: float
    details: dict[str, Any]
    backend: str  # "adk" | "deepeval"

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass
class RunContext:
    run_id: str
    suite_id: str
    timeout_s: float = 300.0
    model_override: str | None = None
