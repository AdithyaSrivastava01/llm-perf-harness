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

    # Simulate tool calling for math
    if any(w in user_msg for w in ["calculate", "math", "15", "25", "*", "+"]):
        return {
            "id": f"mock-{uuid.uuid4().hex[:8]}",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The answer is 352.",
                    "tool_calls": [{
                        "type": "function",
                        "function": {"name": "calculator", "arguments": json.dumps({"expression": "15*23+7"})},
                    }],
                },
            }],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }

    # Simulate RAG for knowledge questions
    if any(w in user_msg for w in ["knowledge", "document", "information", "based on"]):
        return {
            "id": f"mock-{uuid.uuid4().hex[:8]}",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Based on the retrieved documents, I can help with Python, FastAPI, and machine learning topics. According to our source documents, Python was created by Guido van Rossum.",
                },
            }],
            "usage": {"prompt_tokens": 25, "completion_tokens": 30},
        }

    # Default response
    return {
        "id": f"mock-{uuid.uuid4().hex[:8]}",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"I'm a helpful AI assistant. I can help with general questions, math calculations using tools, and searching knowledge bases. The capital of France is Paris.",
            },
        }],
        "usage": {"prompt_tokens": 15, "completion_tokens": 20},
    }
