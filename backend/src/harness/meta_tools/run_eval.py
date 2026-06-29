import json
import uuid
from harness.adapters.types import ToolCall, Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.meta_tools.registry import get_adapter, get_default_metrics

async def run_eval(agent_id: str, test_cases_json: str) -> str:
    """Run an evaluation suite against a specific agent."""
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})
    try:
        raw_cases = json.loads(test_cases_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    test_cases = [EvalTestCase(
        id=rc.get("id", str(uuid.uuid4())),
        input=[Turn(role=t["role"], content=t["content"]) for t in rc["input"]],
        expected_output=rc.get("expected_output"),
        expected_tools=[ToolCall(name=t["name"], args=t.get("args", {})) for t in rc.get("expected_tools", [])] or None,
        reference_contexts=rc.get("reference_contexts"), tags=rc.get("tags", []),
    ) for rc in raw_cases]
    metrics = get_default_metrics(agent_id)
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    run_id = str(uuid.uuid4())
    try:
        report = await runner.run(run_id=run_id, suite_id=f"{agent_id}-eval")
    except Exception as e:
        return json.dumps({"error": f"Eval run failed: {e}", "run_id": run_id})
    results = [{"test_case_id": cr.test_case_id, "passed": cr.passed, "latency_ms": round(cr.latency_ms, 1),
        "metrics": [{"name": mr.name, "score": round(mr.score, 3), "passed": mr.passed, "threshold": mr.threshold}
                     for mr in cr.metric_results]} for cr in report.case_results]
    return json.dumps({"run_id": run_id, "overall_passed": report.overall_passed,
        "summary": report.summary(), "results": results}, indent=2)
