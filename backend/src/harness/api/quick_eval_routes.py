from fastapi import APIRouter
from pydantic import BaseModel

from harness.detection.prober import probe_agent
from harness.eval.quick_eval import run_quick_eval

router = APIRouter(prefix="/api", tags=["quick-eval"])


class ProbeRequest(BaseModel):
    endpoint_url: str
    auth_header: str | None = None
    schema_type: str = "openai"


class ProbeResponse(BaseModel):
    reachable: bool
    detected_capabilities: list[str]
    error: str | None = None


class QuickEvalRequest(BaseModel):
    endpoint_url: str
    auth_header: str | None = None
    capabilities: list[str]
    num_cases: int = 5


class QuickEvalResponse(BaseModel):
    run_id: str
    grade_letter: str
    grade_score: float
    pass_rate: float
    total_cases: int
    passed: int
    failed: int
    avg_latency_ms: float
    metric_averages: dict[str, float]
    results: list[dict]


@router.post("/probe", response_model=ProbeResponse)
async def probe_endpoint(req: ProbeRequest) -> ProbeResponse:
    try:
        capabilities, _ = await probe_agent(
            endpoint_url=req.endpoint_url,
            auth_header=req.auth_header,
            schema_type=req.schema_type,
        )
        return ProbeResponse(reachable=True, detected_capabilities=sorted(capabilities))
    except Exception as e:
        return ProbeResponse(reachable=False, detected_capabilities=[], error=str(e))


@router.post("/quick-eval", response_model=QuickEvalResponse)
async def quick_eval_endpoint(req: QuickEvalRequest) -> QuickEvalResponse:
    result = await run_quick_eval(
        endpoint_url=req.endpoint_url,
        capabilities=set(req.capabilities),
        auth_header=req.auth_header,
        num_cases=req.num_cases,
    )
    s = result.summary
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
                    "threshold": mr.threshold,
                }
                for mr in cr.metric_results
            ],
        }
        for cr in result.report.case_results
    ]
    return QuickEvalResponse(
        run_id=result.run_id,
        grade_letter=result.grade.letter,
        grade_score=result.grade.score,
        pass_rate=s.get("pass_rate", 0),
        total_cases=s.get("total_cases", 0),
        passed=s.get("passed", 0),
        failed=s.get("failed", 0),
        avg_latency_ms=s.get("avg_latency_ms", 0),
        metric_averages=s.get("metric_averages", {}),
        results=cases,
    )
