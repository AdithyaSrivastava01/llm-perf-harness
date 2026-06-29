import json
_results_store: dict[str, dict] = {}

def store_results(run_id: str, results: dict) -> None:
    _results_store[run_id] = results

def get_results(run_id: str) -> str:
    """Get the results of a specific eval run."""
    if run_id in _results_store:
        return json.dumps(_results_store[run_id], indent=2)
    return json.dumps({"error": f"Run '{run_id}' not found."})
