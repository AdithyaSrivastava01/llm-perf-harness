from google.adk.agents import LlmAgent
from harness.meta_tools.explain_failure import explain_failure
from harness.meta_tools.list_agents import list_agents
from harness.meta_tools.list_metrics import list_metrics
from harness.meta_tools.run_eval import run_eval

META_AGENT_INSTRUCTION = """You are the Agent-Evals Meta-Harness — an evaluation orchestrator.
You help users understand and evaluate their AI agents' quality.

Capabilities:
1. List available demo agents (use list_agents)
2. Show metrics per agent type (use list_metrics)
3. Run evaluation suites (use run_eval)
4. Explain failures (use explain_failure)

When running evals, construct test cases as a JSON array with: id, input, expected_output, expected_tools, reference_contexts.
Be concise. Highlight failures first."""

def create_meta_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(name="meta_agent", model=model, instruction=META_AGENT_INSTRUCTION,
        tools=[list_agents, list_metrics, run_eval, explain_failure])
