import inspect
from harness.adapters.rag import RAGAdapter


def test_rag_adapter_has_protocol_methods() -> None:
    assert hasattr(RAGAdapter, "agent_id")
    assert hasattr(RAGAdapter, "display_name")
    assert hasattr(RAGAdapter, "capabilities")
    assert hasattr(RAGAdapter, "invoke")
    assert hasattr(RAGAdapter, "supported_metrics")
    assert hasattr(RAGAdapter, "expected_tools")
    assert hasattr(RAGAdapter, "reference_contexts")
    assert inspect.iscoroutinefunction(RAGAdapter.invoke)


def test_rag_adapter_supported_metrics() -> None:
    # These don't need __init__ since they're simple method defs
    adapter = object.__new__(RAGAdapter)
    metrics = RAGAdapter.supported_metrics(adapter)
    assert "faithfulness" in metrics
    assert "hallucination" in metrics
    assert "contextual_relevancy" in metrics
    assert "answer_relevancy" in metrics
