import json

_pending_cases: dict[str, list[dict]] = {}


def store_pending_cases(agent_id: str, cases: list[dict]) -> None:
    _pending_cases[agent_id] = cases


def review_test_cases(agent_id: str, action: str, case_ids: str = "") -> str:
    """Review generated test cases — approve, reject, or list pending cases."""
    if agent_id not in _pending_cases:
        return json.dumps(
            {"error": f"No pending cases for agent '{agent_id}'. Generate cases first."}
        )
    cases = _pending_cases[agent_id]
    if action == "list":
        return json.dumps(
            {"agent_id": agent_id, "total_pending": len(cases), "cases": cases},
            indent=2,
        )
    if action == "approve_all":
        for case in cases:
            case["approved"] = True
        return json.dumps(
            {
                "agent_id": agent_id,
                "approved_count": len(cases),
                "message": "All cases approved.",
            }
        )
    target_ids = {cid.strip() for cid in case_ids.split(",") if cid.strip()}
    if not target_ids:
        return json.dumps({"error": "No case_ids provided."})
    if action == "approve":
        approved = sum(
            1
            for c in cases
            if c["id"] in target_ids and not c.setdefault("approved", True)
        )
        return json.dumps(
            {
                "approved_count": len(target_ids),
                "total_pending": len([c for c in cases if not c.get("approved")]),
            }
        )
    if action == "reject":
        before = len(cases)
        _pending_cases[agent_id] = [c for c in cases if c["id"] not in target_ids]
        return json.dumps(
            {
                "rejected_count": before - len(_pending_cases[agent_id]),
                "remaining": len(_pending_cases[agent_id]),
            }
        )
    return json.dumps(
        {
            "error": f"Unknown action '{action}'. Use list, approve_all, approve, or reject."
        }
    )


def get_approved_cases(agent_id: str) -> list[dict]:
    return [c for c in _pending_cases.get(agent_id, []) if c.get("approved")]
