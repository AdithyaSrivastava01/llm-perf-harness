import json
from harness.meta_tools.get_results import _results_store

_baselines: dict[str, dict] = {}


def promote_baseline(run_id: str, agent_id: str) -> str:
    """Promote an eval run to be the golden baseline for regression detection."""
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})
    run_data = _results_store[run_id]
    summary = run_data.get("summary", {})
    metric_averages = summary.get("metric_averages", {})
    if not metric_averages:
        return json.dumps({"error": "Run has no metric scores to use as baseline"})
    _baselines[f"{agent_id}:default"] = {
        "run_id": run_id,
        "agent_id": agent_id,
        "scores": metric_averages,
        "pass_rate": summary.get("pass_rate", 0),
    }
    return json.dumps(
        {
            "message": f"Baseline set for agent '{agent_id}'",
            "run_id": run_id,
            "scores": metric_averages,
            "pass_rate": summary.get("pass_rate", 0),
        },
        indent=2,
    )


def get_baseline(agent_id: str) -> dict | None:
    return _baselines.get(f"{agent_id}:default")
