from dataclasses import dataclass
from typing import Any

from harness.adapters.types import AgentResponse, MetricResult


@dataclass
class CaseResult:
    test_case_id: str
    metric_results: list[MetricResult]
    latency_ms: float
    agent_response: AgentResponse | None = None

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metric_results)


@dataclass
class EvalReport:
    run_id: str
    suite_id: str
    case_results: list[CaseResult]

    @property
    def overall_passed(self) -> bool:
        return all(cr.passed for cr in self.case_results)

    def summary(self) -> dict[str, Any]:
        total = len(self.case_results)
        passed = sum(1 for cr in self.case_results if cr.passed)
        latencies = [cr.latency_ms for cr in self.case_results]
        avg_latency = sum(latencies) / total if total > 0 else 0.0
        metric_scores: dict[str, list[float]] = {}
        for cr in self.case_results:
            for mr in cr.metric_results:
                metric_scores.setdefault(mr.name, []).append(mr.score)
        avg_scores = {name: sum(scores) / len(scores) for name, scores in metric_scores.items()}
        return {
            "total_cases": total, "passed": passed, "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "avg_latency_ms": avg_latency, "metric_averages": avg_scores,
        }
