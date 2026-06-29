from google.adk.agents import LlmAgent

from harness.meta_tools.compare_runs import compare_runs
from harness.meta_tools.connect_agent import connect_agent
from harness.meta_tools.explain_failure import explain_failure
from harness.meta_tools.generate_test_cases import generate_test_cases
from harness.meta_tools.list_agents import list_agents
from harness.meta_tools.list_metrics import list_metrics
from harness.meta_tools.promote_baseline import promote_baseline
from harness.meta_tools.quick_eval_tool import quick_eval
from harness.meta_tools.review_test_cases import review_test_cases
from harness.meta_tools.run_eval import run_eval

META_AGENT_INSTRUCTION = """You are the Agent-Evals Meta-Harness — an evaluation orchestrator.
You help users understand and evaluate their AI agents' quality.

Capabilities:
1. List available demo agents (use list_agents)
2. Show metrics per agent type (use list_metrics)
3. Run evaluation suites (use run_eval)
4. Explain failures (use explain_failure)
5. Generate test cases automatically (use generate_test_cases)
6. Let users review and approve cases (use review_test_cases)
7. Compare runs against baseline (use compare_runs)
8. Promote a run to baseline (use promote_baseline)
9. Connect external agent endpoints (use connect_agent)
10. Run quick evaluations on external agents (use quick_eval)
For external agents: connect_agent (paste URL) → confirm capabilities → quick_eval.

When running evals, construct test cases as a JSON array with: id, input, expected_output, expected_tools, reference_contexts.
Be concise. Highlight failures first."""


def create_meta_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name="meta_agent",
        model=model,
        instruction=META_AGENT_INSTRUCTION,
        tools=[
            list_agents,
            list_metrics,
            run_eval,
            explain_failure,
            generate_test_cases,
            review_test_cases,
            compare_runs,
            promote_baseline,
            connect_agent,
            quick_eval,
        ],
    )
