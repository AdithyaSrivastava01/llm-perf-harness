import uuid
from dataclasses import dataclass
from typing import Any

from harness.adapters.http_agent import HTTPAgentAdapter
from harness.adapters.types import Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.eval.grader import GradeResult, calculate_grade
from harness.eval.metrics import MetricBackend, MetricConfig
from harness.eval.report import EvalReport

CAPABILITY_METRICS: dict[str, list[MetricConfig]] = {
    "text": [
        MetricConfig(
            name="response_match_score",
            backend=MetricBackend.ADK,
            threshold=0.05,
        )
    ],
    "tools": [
        MetricConfig(
            name="tool_trajectory_avg_score",
            backend=MetricBackend.ADK,
            threshold=0.5,
        ),
    ],
    "rag": [
        MetricConfig(
            name="response_match_score",
            backend=MetricBackend.ADK,
            threshold=0.05,
        ),
    ],
}

QUICK_TEST_CASES = [
    {
        "input": "What can you help me with?",
        "expected_output": "help assistant questions",
        "tags": ["general"],
    },
    {
        "input": "What is the capital of France?",
        "expected_output": "Paris",
        "tags": ["knowledge"],
    },
    {
        "input": "Summarize your main capabilities in one sentence.",
        "expected_output": "help assistant",
        "tags": ["general"],
    },
    {"input": "What is 25 * 4?", "expected_output": "100", "tags": ["math"]},
    {
        "input": "Explain what you do in simple terms.",
        "expected_output": "help questions assistant",
        "tags": ["general"],
    },
]


@dataclass
class QuickEvalResult:
    run_id: str
    grade: GradeResult
    report: EvalReport
    capabilities: set[str]
    summary: dict[str, Any]


async def run_quick_eval(
    endpoint_url: str,
    capabilities: set[str],
    auth_header: str | None = None,
    num_cases: int = 5,
) -> QuickEvalResult:
    adapter = HTTPAgentAdapter(
        endpoint_url=endpoint_url,
        auth_header=auth_header,
        detected_capabilities=capabilities,
    )
    metrics: list[MetricConfig] = []
    for cap in capabilities:
        metrics.extend(CAPABILITY_METRICS.get(cap, []))
    test_cases = [
        EvalTestCase(
            id=f"quick-{i}",
            input=[Turn(role="user", content=tc["input"])],
            expected_output=tc.get("expected_output"),
            expected_tools=None,
            reference_contexts=None,
            tags=tc["tags"],
        )
        for i, tc in enumerate(QUICK_TEST_CASES[:num_cases])
    ]
    run_id = str(uuid.uuid4())
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id=run_id, suite_id="quick-eval")
    summary = report.summary()
    grade = calculate_grade(summary.get("metric_averages", {}))
    return QuickEvalResult(
        run_id=run_id,
        grade=grade,
        report=report,
        capabilities=capabilities,
        summary=summary,
    )
