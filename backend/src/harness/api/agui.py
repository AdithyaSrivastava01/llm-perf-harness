from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from fastapi import FastAPI
from harness.agents.meta_agent import create_meta_agent

def setup_agui_endpoint(app: FastAPI) -> None:
    meta_agent = create_meta_agent()
    adk_agent = ADKAgent(adk_agent=meta_agent, app_name="agent-evals-harness",
        user_id="default-user", use_in_memory_services=True,
        session_timeout_seconds=3600, execution_timeout_seconds=600)
    add_adk_fastapi_endpoint(app, adk_agent, path="/agui")
