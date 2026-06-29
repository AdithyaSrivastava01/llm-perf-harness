import json
from harness.meta_tools.get_results import _results_store
from harness.meta_tools.promote_baseline import get_baseline


def compare_runs(run_id: str, agent_id: str) -> str:
    """Compare an eval run against the current baseline, highlighting regressions."""
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})
    baseline = get_baseline(agent_id)
    if baseline is None:
        return json.dumps(
            {
                "message": f"No baseline set for agent '{agent_id}'. Promote a run first.",
                "run_id": run_id,
            }
        )
    current_scores = (
        _results_store[run_id].get("summary", {}).get("metric_averages", {})
    )
    baseline_scores = baseline["scores"]
    deltas, regressions, improvements = {}, [], []
    tolerance = 0.05
    for metric, bs in baseline_scores.items():
        current = current_scores.get(metric)
        if current is None:
            continue
        delta = current - bs
        deltas[metric] = round(delta, 4)
        entry = {
            "metric": metric,
            "baseline": round(bs, 3),
            "current": round(current, 3),
            "delta": round(delta, 3),
        }
        if delta < -tolerance:
            regressions.append(entry)
        elif delta > tolerance:
            improvements.append(entry)
    return json.dumps(
        {
            "run_id": run_id,
            "baseline_run_id": baseline["run_id"],
            "has_regressions": len(regressions) > 0,
            "regressions": regressions,
            "improvements": improvements,
            "deltas": deltas,
        },
        indent=2,
    )
