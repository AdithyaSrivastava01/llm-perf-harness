"""Mock OpenAI-compatible agent endpoint for testing Quick Eval."""

import json
import time
import uuid

from fastapi import APIRouter

from pydantic import BaseModel

router = APIRouter(tags=["mock"])


class MockMessage(BaseModel):
    role: str
    content: str


class MockRequest(BaseModel):
    messages: list[MockMessage]
    temperature: float = 0


@router.post("/v1/chat/completions")
async def mock_completions(req: MockRequest) -> dict:
    user_msg = req.messages[-1].content.lower() if req.messages else ""

    # Math questions — use tool
    if any(w in user_msg for w in ["25 * 4", "25*4", "calculate", "math"]):
        return _response(
            "The answer is 100.",
            tool_calls=[
                {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "arguments": json.dumps({"expression": "25*4"}),
                    },
                }
            ],
        )

    # Capital question
    if "capital" in user_msg and "france" in user_msg:
        return _response("The capital of France is Paris.")

    # Knowledge/RAG questions
    if any(w in user_msg for w in ["knowledge", "document", "information", "based on"]):
        return _response(
            "Based on the retrieved documents, I can help with Python, FastAPI, and machine learning topics.",
        )

    # Capabilities question
    if any(w in user_msg for w in ["help", "capabilities", "can you", "what do you"]):
        return _response(
            "I'm a helpful assistant. I can help with general questions, math calculations using tools, and searching knowledge bases.",
        )

    # Summarize
    if "summarize" in user_msg or "simple terms" in user_msg or "explain" in user_msg:
        return _response(
            "I help answer questions, perform calculations using tools, and search knowledge bases to assist you.",
        )

    # Default
    return _response(
        "I'm a helpful AI assistant. I can help with a wide range of questions and tasks."
    )


def _response(content: str, tool_calls: list | None = None) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": f"mock-{uuid.uuid4().hex[:8]}",
        "choices": [{"index": 0, "message": message}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 15},
    }
