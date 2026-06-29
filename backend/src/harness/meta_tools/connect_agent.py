import json

from harness.detection.prober import probe_agent


async def connect_agent(endpoint_url: str, auth_header: str = "") -> str:
    """Connect to an external agent endpoint and detect its capabilities."""
    try:
        capabilities, responses = await probe_agent(
            endpoint_url=endpoint_url, auth_header=auth_header or None
        )
        return json.dumps(
            {
                "reachable": True,
                "endpoint_url": endpoint_url,
                "detected_capabilities": sorted(capabilities),
                "probe_summary": [
                    {
                        "probe": i + 1,
                        "response_length": len(r.output),
                        "tool_calls": len(r.tool_calls),
                    }
                    for i, r in enumerate(responses)
                ],
                "message": (
                    f"Agent detected with capabilities: {', '.join(sorted(capabilities))}. "
                    "Confirm before running eval."
                ),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"reachable": False, "error": str(e)})
