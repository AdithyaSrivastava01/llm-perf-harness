import json
from harness.meta_tools.registry import list_adapters

def list_agents() -> str:
    """List all available agents with their capabilities and supported metrics."""
    agents = [{"agent_id": a.agent_id, "display_name": a.display_name,
        "capabilities": sorted(a.capabilities), "supported_metrics": a.supported_metrics()}
        for a in list_adapters().values()]
    return json.dumps(agents, indent=2)
