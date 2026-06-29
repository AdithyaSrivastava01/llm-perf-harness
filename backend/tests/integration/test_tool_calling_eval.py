import inspect

from harness.adapters.tool_calling import ToolCallingAdapter


def test_tool_calling_adapter_has_protocol_methods() -> None:
    assert hasattr(ToolCallingAdapter, "agent_id")
    assert hasattr(ToolCallingAdapter, "display_name")
    assert hasattr(ToolCallingAdapter, "capabilities")
    assert hasattr(ToolCallingAdapter, "invoke")
    assert hasattr(ToolCallingAdapter, "supported_metrics")
    assert hasattr(ToolCallingAdapter, "expected_tools")
    assert hasattr(ToolCallingAdapter, "reference_contexts")
    assert inspect.iscoroutinefunction(ToolCallingAdapter.invoke)
