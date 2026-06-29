import json

from harness.eval.quick_eval import run_quick_eval


async def quick_eval(
    endpoint_url: str,
    capabilities: str,
    auth_header: str = "",
    num_cases: int = 5,
) -> str:
    """Run a quick evaluation against an external agent endpoint."""
    caps = {c.strip() for c in capabilities.split(",") if c.strip()}
    try:
        result = await run_quick_eval(
            endpoint_url=endpoint_url,
            capabilities=caps,
            auth_header=auth_header or None,
            num_cases=min(num_cases, 10),
        )
        cases = [
            {
                "test_case_id": cr.test_case_id,
                "passed": cr.passed,
                "latency_ms": round(cr.latency_ms, 1),
                "metrics": [
                    {
                        "name": mr.name,
                        "score": round(mr.score, 3),
                        "passed": mr.passed,
                    }
                    for mr in cr.metric_results
                ],
            }
            for cr in result.report.case_results
        ]
        return json.dumps(
            {
                "run_id": result.run_id,
                "grade": result.grade.letter,
                "score": result.grade.score,
                "summary": result.summary,
                "results": cases,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Quick eval failed: {e}"})
