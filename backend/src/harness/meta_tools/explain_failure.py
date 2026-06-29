import json
from harness.meta_tools.get_results import _results_store

def explain_failure(run_id: str, test_case_id: str) -> str:
    """Explain why a specific test case failed in an eval run."""
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})
    for result in _results_store[run_id].get("results", []):
        if result["test_case_id"] == test_case_id:
            failures = [m for m in result["metrics"] if not m["passed"]]
            explanation = " ".join(f"Metric '{f['name']}' scored {f['score']:.3f}, below threshold {f['threshold']:.3f}." for f in failures) if failures else "All metrics passed."
            return json.dumps({"test_case_id": test_case_id, "passed": result["passed"],
                "failing_metrics": failures, "all_metrics": result["metrics"], "explanation": explanation}, indent=2)
    return json.dumps({"error": f"Test case '{test_case_id}' not found in run '{run_id}'"})
