from google.adk.agents import LlmAgent

from harness.agents.tools import calculate, get_weather, search_knowledge

TOOL_CALLING_INSTRUCTION = """You are a helpful assistant with access to tools.
Use get_weather to answer weather questions.
Use calculate for math problems.
Use search_knowledge for general knowledge questions.
Always use the appropriate tool before answering. Do not guess."""


def create_tool_calling_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name="tool_calling_agent",
        model=model,
        instruction=TOOL_CALLING_INSTRUCTION,
        tools=[get_weather, calculate, search_knowledge],
    )
