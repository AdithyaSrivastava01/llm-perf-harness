from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from harness.adapters.types import AgentResponse, MetricResult, ToolCall


class MetricBackend(Enum):
    ADK = "adk"
    DEEPEVAL = "deepeval"


@dataclass(frozen=True)
class MetricConfig:
    name: str
    backend: MetricBackend
    threshold: float
    params: dict[str, Any] = field(default_factory=dict)


def route_metrics(
    all_configs: list[MetricConfig], supported: list[str]
) -> list[MetricConfig]:
    supported_set = set(supported)
    return [c for c in all_configs if c.name in supported_set]


async def compute_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    expected_tools: list[ToolCall] | None,
    reference_contexts: list[str] | None,
) -> MetricResult:
    if config.backend == MetricBackend.ADK:
        score = await _compute_adk_metric(
            config, agent_response, expected_output, expected_tools
        )
    elif config.backend == MetricBackend.DEEPEVAL:
        score = await _compute_deepeval_metric(
            config, agent_response, expected_output, reference_contexts
        )
    else:
        raise ValueError(f"Unknown backend: {config.backend}")
    return MetricResult(
        name=config.name,
        score=score,
        threshold=config.threshold,
        details={"backend": config.backend.value},
        backend=config.backend.value,
    )


async def _compute_adk_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    expected_tools: list[ToolCall] | None,
) -> float:
    if config.name == "tool_trajectory_avg_score":
        return _tool_trajectory_score(agent_response.tool_calls, expected_tools or [])
    elif config.name == "response_match_score":
        return _rouge1_score(agent_response.output, expected_output or "")
    elif config.name == "final_response_match_v2":
        return _rouge1_score(agent_response.output, expected_output or "")
    else:
        raise ValueError(f"Unknown ADK metric: {config.name}")


async def _compute_deepeval_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    reference_contexts: list[str] | None,
) -> float:
    import asyncio

    def _run_deepeval() -> float:
        import time as _time

        from deepeval.metrics import (
            AnswerRelevancyMetric,
            ContextualRelevancyMetric,
            FaithfulnessMetric,
            HallucinationMetric,
        )
        from deepeval.models.llms.litellm_model import LiteLLMModel
        from deepeval.test_case import LLMTestCase

        from harness.config import settings

        judge_model = LiteLLMModel(
            model="gemini/gemini-2.5-flash",
            api_key=settings.google_api_key,
        )

        test_case = LLMTestCase(
            input=expected_output or "",
            actual_output=agent_response.output,
            expected_output=expected_output,
            retrieval_context=reference_contexts or [],
            context=reference_contexts or [],
        )
        metric_map = {
            "faithfulness": FaithfulnessMetric,
            "contextual_relevancy": ContextualRelevancyMetric,
            "hallucination": HallucinationMetric,
            "answer_relevancy": AnswerRelevancyMetric,
        }
        metric_cls = metric_map.get(config.name)
        if metric_cls is None:
            raise ValueError(f"Unknown DeepEval metric: {config.name}")
        metric = metric_cls(threshold=config.threshold, model=judge_model)

        # Retry with backoff for rate limits
        for attempt in range(3):
            try:
                metric.measure(test_case)
                return metric.score
            except Exception as e:
                if (
                    "429" in str(e)
                    or "rate" in str(e).lower()
                    or "quota" in str(e).lower()
                ):
                    wait = 20 * (attempt + 1)
                    _time.sleep(wait)
                else:
                    raise
        metric.measure(test_case)
        return metric.score

    return await asyncio.to_thread(_run_deepeval)


def _tool_trajectory_score(actual: list[ToolCall], expected: list[ToolCall]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    actual_names = [tc.name for tc in actual]
    expected_names = [tc.name for tc in expected]
    if actual_names == expected_names:
        return 1.0
    matches = 0
    actual_idx = 0
    for exp_name in expected_names:
        while actual_idx < len(actual_names):
            if actual_names[actual_idx] == exp_name:
                matches += 1
                actual_idx += 1
                break
            actual_idx += 1
    return matches / len(expected_names)


def _rouge1_score(generated: str, reference: str) -> float:
    if not reference or not generated:
        return 0.0
    gen_tokens = set(generated.lower().split())
    ref_tokens = set(reference.lower().split())
    if not ref_tokens:
        return 0.0
    overlap = gen_tokens & ref_tokens
    precision = len(overlap) / len(gen_tokens) if gen_tokens else 0.0
    recall = len(overlap) / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)
