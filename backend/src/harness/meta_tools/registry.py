from harness.eval.metrics import MetricBackend, MetricConfig

_adapters: dict = {}
_default_metrics: dict[str, list[MetricConfig]] = {}


def init_registry() -> None:
    from harness.adapters.rag import RAGAdapter
    from harness.adapters.tool_calling import ToolCallingAdapter

    global _adapters, _default_metrics
    tool_adapter = ToolCallingAdapter()
    rag_adapter = RAGAdapter()
    _adapters = {tool_adapter.agent_id: tool_adapter, rag_adapter.agent_id: rag_adapter}
    _default_metrics = {
        "tool-calling-agent": [
            MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
            MetricConfig(name="final_response_match_v2", backend=MetricBackend.ADK, threshold=0.7),
            MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
        ],
        "rag-agent": [
            MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
            MetricConfig(name="contextual_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
            MetricConfig(name="hallucination", backend=MetricBackend.DEEPEVAL, threshold=0.8),
            MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
        ],
    }


def get_adapter(agent_id: str):
    return _adapters.get(agent_id)


def list_adapters() -> dict:
    return dict(_adapters)


def get_default_metrics(agent_id: str) -> list[MetricConfig]:
    return _default_metrics.get(agent_id, [])
