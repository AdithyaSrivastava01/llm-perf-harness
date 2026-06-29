from dataclasses import dataclass

from harness.adapters.protocol import AgentAdapter
from harness.adapters.types import RunContext, ToolCall, Turn
from harness.eval.metrics import MetricConfig, compute_metric, route_metrics
from harness.eval.report import CaseResult, EvalReport


@dataclass
class EvalTestCase:
    id: str
    input: list[Turn]
    expected_output: str | None
    expected_tools: list[ToolCall] | None
    reference_contexts: list[str] | None
    tags: list[str]


class EvalRunner:
    def __init__(
        self,
        adapter: AgentAdapter,
        metrics: list[MetricConfig],
        test_cases: list[EvalTestCase],
    ) -> None:
        self._adapter = adapter
        self._metrics = route_metrics(metrics, adapter.supported_metrics())
        self._test_cases = test_cases

    async def run(self, run_id: str, suite_id: str) -> EvalReport:
        ctx = RunContext(run_id=run_id, suite_id=suite_id)
        case_results: list[CaseResult] = []

        for tc in self._test_cases:
            response = await self._adapter.invoke(tc.input, ctx)

            metric_results = []
            for metric_config in self._metrics:
                result = await compute_metric(
                    config=metric_config,
                    agent_response=response,
                    expected_output=tc.expected_output,
                    expected_tools=tc.expected_tools,
                    reference_contexts=tc.reference_contexts,
                )
                metric_results.append(result)

            case_results.append(
                CaseResult(
                    test_case_id=tc.id,
                    metric_results=metric_results,
                    latency_ms=response.latency_ms,
                    agent_response=response,
                )
            )

        return EvalReport(run_id=run_id, suite_id=suite_id, case_results=case_results)
