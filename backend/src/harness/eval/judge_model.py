"""Gemini judge model for DeepEval metrics via LiteLLM."""
from harness.config import settings


def get_judge_model():
    """Create a DeepEval-compatible judge model using Gemini via LiteLLM."""
    from deepeval.models.llms.litellm_model import LiteLLMModel

    return LiteLLMModel(
        model="gemini/gemini-2.5-flash",
        api_key=settings.google_api_key,
    )
