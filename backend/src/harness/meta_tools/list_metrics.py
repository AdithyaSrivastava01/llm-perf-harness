import json
from harness.meta_tools.registry import get_adapter, get_default_metrics

def list_metrics(agent_id: str) -> str:
    """List available metrics and their default thresholds for a specific agent."""
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})
    defaults = get_default_metrics(agent_id)
    metrics = [{"name": m.name, "backend": m.backend.value, "threshold": m.threshold}
               for m in defaults if m.name in adapter.supported_metrics()]
    return json.dumps(metrics, indent=2)
