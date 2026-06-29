# Plug-and-Play Eval Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "paste URL → get quality report in 2 minutes" flow: HTTPAgentAdapter, auto-detection, quick eval endpoint, report card UI, BYOK key storage, and workspace isolation (org_id).

**Architecture:** HTTPAgentAdapter implements existing AgentAdapter Protocol to connect to any OpenAI-compatible agent endpoint. Auto-detection probes the agent with 3 messages to classify capabilities. Quick eval orchestrates detect → generate → eval → grade into a single flow. Report card is a two-tier UI (grade summary + per-case detail). BYOK keys encrypted with Fernet.

**Tech Stack:** httpx (async HTTP client), cryptography (Fernet encryption), existing FastAPI + eval engine + CopilotKit frontend.

**Spec:** `docs/superpowers/specs/2026-06-28-plug-and-play-eval-design.md`

---

## File Structure

```
backend/src/harness/
├── adapters/
│   └── http_agent.py          # NEW: HTTPAgentAdapter
├── detection/
│   ├── __init__.py             # NEW
│   ├── prober.py               # NEW: sends probe messages, collects responses
│   └── classifier.py           # NEW: classifies capabilities from probe results
├── eval/
│   ├── grader.py               # NEW: calculates letter grade from metric scores
│   └── quick_eval.py           # NEW: orchestrates full quick eval flow
├── crypto.py                   # NEW: Fernet encrypt/decrypt helpers
├── meta_tools/
│   ├── connect_agent.py        # NEW: meta-agent tool for connecting external agents
│   └── quick_eval_tool.py      # NEW: meta-agent tool wrapping quick eval
├── api/
│   └── quick_eval_routes.py    # NEW: REST endpoints for quick eval
├── db/
│   └── models.py               # MODIFY: add org_id, UserSettings, ConnectedAgent
├── config.py                   # MODIFY: add encryption_key setting

backend/tests/
├── unit/
│   ├── test_http_agent.py      # NEW
│   ├── test_prober.py          # NEW
│   ├── test_classifier.py      # NEW
│   ├── test_grader.py          # NEW
│   └── test_crypto.py          # NEW
├── integration/
│   └── test_quick_eval.py      # NEW

frontend/src/
├── app/
│   └── quick-eval/
│       └── page.tsx            # NEW: Quick Eval landing page
├── components/
│   ├── report-card.tsx         # NEW: grade summary + metric bars
│   └── case-detail.tsx         # NEW: expandable per-case results
```

---

## Task 1: Crypto Helpers + Config

**Files:**
- Create: `backend/src/harness/crypto.py`
- Modify: `backend/src/harness/config.py`
- Create: `backend/tests/unit/test_crypto.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_crypto.py
from harness.crypto import encrypt_value, decrypt_value


def test_encrypt_decrypt_roundtrip() -> None:
    original = "sk-test-api-key-12345"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert decrypt_value(encrypted) == original


def test_encrypt_produces_different_output_each_time() -> None:
    value = "same-input"
    enc1 = encrypt_value(value)
    enc2 = encrypt_value(value)
    assert enc1 != enc2  # Fernet uses random IV


def test_decrypt_invalid_token_returns_none() -> None:
    result = decrypt_value("not-a-valid-fernet-token")
    assert result is None
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd backend && uv run pytest tests/unit/test_crypto.py -v
```

- [ ] **Step 3: Add cryptography dependency**

```bash
cd backend && uv add cryptography
```

- [ ] **Step 4: Add encryption_key to config**

Add to `backend/src/harness/config.py` in the Settings class:

```python
    encryption_key: str = Field(
        default="dev-encryption-key-change-in-prod-32b=",
        alias="HARNESS_ENCRYPTION_KEY",
    )
```

- [ ] **Step 5: Implement crypto helpers**

```python
# backend/src/harness/crypto.py
from cryptography.fernet import Fernet, InvalidToken

from harness.config import settings


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    # Pad or hash to 32 bytes, base64 encode for Fernet
    import base64
    import hashlib
    key_bytes = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str | None:
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return None
```

- [ ] **Step 6: Run tests**

```bash
cd backend && uv run pytest tests/unit/test_crypto.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/harness/crypto.py backend/src/harness/config.py backend/tests/unit/test_crypto.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add Fernet encryption helpers and encryption_key config"
```

---

## Task 2: Data Model Updates

**Files:**
- Modify: `backend/src/harness/db/models.py`
- Create: `backend/tests/unit/test_new_models.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_new_models.py
import uuid
from harness.db.models import ConnectedAgent, UserSettings


def test_user_settings_defaults() -> None:
    us = UserSettings(user_id=uuid.uuid4(), judge_provider="gemini")
    assert us.judge_provider == "gemini"
    assert us.judge_api_key_enc is None


def test_connected_agent_fields() -> None:
    ca = ConnectedAgent(
        user_id=uuid.uuid4(),
        endpoint_url="https://my-agent.com/v1/chat/completions",
        schema_type="openai",
        detected_capabilities=["text", "tools"],
        confirmed_capabilities=["text", "tools"],
        display_name="My Agent",
    )
    assert ca.endpoint_url == "https://my-agent.com/v1/chat/completions"
    assert ca.schema_type == "openai"
    assert "tools" in ca.detected_capabilities
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd backend && uv run pytest tests/unit/test_new_models.py -v
```

- [ ] **Step 3: Add models to db/models.py**

Add `org_id` to User class:
```python
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
```

Add two new model classes at end of file:

```python
class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    judge_provider: Mapped[str] = mapped_column(String, nullable=False, default="gemini")
    judge_api_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConnectedAgent(Base):
    __tablename__ = "connected_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_header_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_type: Mapped[str] = mapped_column(String, nullable=False, default="openai")
    custom_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    detected_capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    confirmed_capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_probed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_connected_agents_user_id", "user_id"),)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/unit/test_new_models.py -v
```

- [ ] **Step 5: Generate migration**

```bash
cd backend && uv run alembic revision --autogenerate -m "add user_settings connected_agents org_id"
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/harness/db/models.py backend/tests/unit/test_new_models.py backend/alembic/
git commit -m "feat: add UserSettings, ConnectedAgent models and org_id"
```

---

## Task 3: HTTPAgentAdapter

**Files:**
- Create: `backend/src/harness/adapters/http_agent.py`
- Create: `backend/tests/unit/test_http_agent.py`

- [ ] **Step 1: Add httpx dependency**

```bash
cd backend && uv add httpx
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/unit/test_http_agent.py
import json
import pytest
from unittest.mock import AsyncMock, patch

from harness.adapters.http_agent import HTTPAgentAdapter, parse_openai_response
from harness.adapters.types import RunContext, Turn


def test_parse_openai_response_text_only() -> None:
    raw = {
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}, "index": 0}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    output, tool_calls, usage = parse_openai_response(raw)
    assert output == "Hello!"
    assert tool_calls == []
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5


def test_parse_openai_response_with_tool_calls() -> None:
    raw = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"function": {"name": "get_weather", "arguments": '{"city": "Paris"}'}, "type": "function"}
                ],
            },
            "index": 0,
        }],
        "usage": {"prompt_tokens": 15, "completion_tokens": 8},
    }
    output, tool_calls, usage = parse_openai_response(raw)
    assert output == ""
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "get_weather"
    assert tool_calls[0].args == {"city": "Paris"}


def test_parse_openai_response_missing_usage() -> None:
    raw = {"choices": [{"message": {"content": "Hi"}}]}
    output, tool_calls, usage = parse_openai_response(raw)
    assert output == "Hi"
    assert usage.input_tokens == 0


def test_http_adapter_metadata() -> None:
    adapter = HTTPAgentAdapter(
        endpoint_url="https://example.com/v1/chat/completions",
        detected_capabilities={"text", "tools"},
    )
    assert adapter.agent_id.startswith("http-")
    assert adapter.display_name == "https://example.com/v1/chat/completions"
    assert adapter.capabilities == {"text", "tools"}
    assert "tool_trajectory_avg_score" in adapter.supported_metrics()


def test_http_adapter_supported_metrics_text_only() -> None:
    adapter = HTTPAgentAdapter(
        endpoint_url="https://example.com",
        detected_capabilities={"text"},
    )
    metrics = adapter.supported_metrics()
    assert "answer_relevancy" in metrics
    assert "tool_trajectory_avg_score" not in metrics
    assert "faithfulness" not in metrics


def test_http_adapter_supported_metrics_rag() -> None:
    adapter = HTTPAgentAdapter(
        endpoint_url="https://example.com",
        detected_capabilities={"text", "rag"},
    )
    metrics = adapter.supported_metrics()
    assert "faithfulness" in metrics
    assert "hallucination" in metrics
```

- [ ] **Step 3: Run tests to verify failure**

```bash
cd backend && uv run pytest tests/unit/test_http_agent.py -v
```

- [ ] **Step 4: Implement HTTPAgentAdapter**

```python
# backend/src/harness/adapters/http_agent.py
import hashlib
import json
import time
from typing import Any

import httpx

from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn


def parse_openai_response(raw: dict) -> tuple[str, list[ToolCall], TokenUsage]:
    """Parse an OpenAI-compatible chat completion response."""
    choices = raw.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}

    output = message.get("content") or ""

    tool_calls = []
    for tc in message.get("tool_calls", []):
        func = tc.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(name=name, args=args))

    usage_raw = raw.get("usage", {})
    usage = TokenUsage(
        input_tokens=usage_raw.get("prompt_tokens", 0),
        output_tokens=usage_raw.get("completion_tokens", 0),
    )

    return output, tool_calls, usage


class HTTPAgentAdapter:
    def __init__(
        self,
        endpoint_url: str,
        auth_header: str | None = None,
        schema_type: str = "openai",
        custom_schema: dict | None = None,
        detected_capabilities: set[str] | None = None,
        display_name: str | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._auth_header = auth_header
        self._schema_type = schema_type
        self._custom_schema = custom_schema
        self._capabilities = detected_capabilities or {"text"}
        self._display_name = display_name

    @property
    def agent_id(self) -> str:
        url_hash = hashlib.sha256(self._endpoint_url.encode()).hexdigest()[:12]
        return f"http-{url_hash}"

    @property
    def display_name(self) -> str:
        return self._display_name or self._endpoint_url

    @property
    def capabilities(self) -> set[str]:
        return self._capabilities

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        messages = [{"role": t.role, "content": t.content} for t in input]
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        payload = {"messages": messages, "temperature": 0}

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=context.timeout_s) as client:
            resp = await client.post(self._endpoint_url, json=payload, headers=headers)
            resp.raise_for_status()
            raw = resp.json()
        elapsed = (time.monotonic() - start) * 1000

        output, tool_calls, usage = parse_openai_response(raw)

        return AgentResponse(
            output=output,
            tool_calls=tool_calls,
            retrieved_contexts=[],
            latency_ms=elapsed,
            token_usage=usage,
            raw_events=[raw],
        )

    def supported_metrics(self) -> list[str]:
        metrics = ["answer_relevancy"]
        if "tools" in self._capabilities:
            metrics.extend(["tool_trajectory_avg_score", "final_response_match_v2"])
        if "rag" in self._capabilities:
            metrics.extend(["faithfulness", "contextual_relevancy", "hallucination"])
        return metrics

    def expected_tools(self) -> list[ToolSpec] | None:
        return None

    def reference_contexts(self) -> list[str] | None:
        return None
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/unit/test_http_agent.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/harness/adapters/http_agent.py backend/tests/unit/test_http_agent.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add HTTPAgentAdapter for external OpenAI-compatible agents"
```

---

## Task 4: Auto-Detection (Prober + Classifier)

**Files:**
- Create: `backend/src/harness/detection/__init__.py`
- Create: `backend/src/harness/detection/prober.py`
- Create: `backend/src/harness/detection/classifier.py`
- Create: `backend/tests/unit/test_prober.py`
- Create: `backend/tests/unit/test_classifier.py`

- [ ] **Step 1: Write classifier tests**

```python
# backend/tests/unit/test_classifier.py
from harness.adapters.types import AgentResponse, TokenUsage, ToolCall
from harness.detection.classifier import classify_capabilities


def _make_response(output: str, tool_calls: list[ToolCall] | None = None) -> AgentResponse:
    return AgentResponse(
        output=output, tool_calls=tool_calls or [], retrieved_contexts=[],
        latency_ms=100.0, token_usage=TokenUsage(input_tokens=10, output_tokens=5),
        raw_events=[],
    )


def test_classify_text_only() -> None:
    responses = [
        _make_response("I can help with general questions."),
        _make_response("I'm not sure about the math."),
        _make_response("I don't have access to a knowledge base."),
    ]
    caps = classify_capabilities(responses)
    assert "text" in caps
    assert "tools" not in caps
    assert "rag" not in caps


def test_classify_tool_use_from_tool_calls() -> None:
    responses = [
        _make_response("I can help."),
        _make_response("The answer is 352.", [ToolCall(name="calculate", args={"expr": "15*23+7"})]),
        _make_response("No knowledge base."),
    ]
    caps = classify_capabilities(responses)
    assert "tools" in caps
    assert "text" in caps


def test_classify_rag_from_response_text() -> None:
    responses = [
        _make_response("I can search documents for you."),
        _make_response("42"),
        _make_response("Based on the retrieved documents, the answer is X."),
    ]
    caps = classify_capabilities(responses)
    assert "rag" in caps


def test_classify_all_capabilities() -> None:
    responses = [
        _make_response("I can search and use tools."),
        _make_response("352", [ToolCall(name="calc", args={})]),
        _make_response("According to the source documents, yes."),
    ]
    caps = classify_capabilities(responses)
    assert caps == {"text", "tools", "rag"}
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && uv run pytest tests/unit/test_classifier.py -v
```

- [ ] **Step 3: Implement classifier**

```python
# backend/src/harness/detection/__init__.py
```

```python
# backend/src/harness/detection/classifier.py
from harness.adapters.types import AgentResponse

RAG_KEYWORDS = [
    "document", "retrieved", "source", "knowledge base", "context",
    "based on", "according to", "reference", "search result",
]


def classify_capabilities(probe_responses: list[AgentResponse]) -> set[str]:
    """Classify agent capabilities from probe responses."""
    caps: set[str] = {"text"}

    for resp in probe_responses:
        if resp.tool_calls:
            caps.add("tools")

        output_lower = resp.output.lower()
        if any(kw in output_lower for kw in RAG_KEYWORDS):
            caps.add("rag")

    return caps
```

- [ ] **Step 4: Run classifier tests**

```bash
cd backend && uv run pytest tests/unit/test_classifier.py -v
```

- [ ] **Step 5: Write prober tests**

```python
# backend/tests/unit/test_prober.py
from harness.detection.prober import PROBE_MESSAGES


def test_probe_messages_exist() -> None:
    assert len(PROBE_MESSAGES) == 3


def test_probe_messages_are_strings() -> None:
    for msg in PROBE_MESSAGES:
        assert isinstance(msg, str)
        assert len(msg) > 0
```

- [ ] **Step 6: Implement prober**

```python
# backend/src/harness/detection/prober.py
from harness.adapters.http_agent import HTTPAgentAdapter
from harness.adapters.types import AgentResponse, RunContext, Turn
from harness.detection.classifier import classify_capabilities

PROBE_MESSAGES = [
    "What can you help me with? What are your capabilities?",
    "What is 15 * 23 + 7?",
    "Based on your knowledge base, what information do you have available?",
]


async def probe_agent(
    endpoint_url: str,
    auth_header: str | None = None,
    schema_type: str = "openai",
) -> tuple[set[str], list[AgentResponse]]:
    """Probe an agent endpoint to detect capabilities.

    Returns (detected_capabilities, probe_responses).
    """
    adapter = HTTPAgentAdapter(
        endpoint_url=endpoint_url,
        auth_header=auth_header,
        schema_type=schema_type,
        detected_capabilities={"text"},
    )

    ctx = RunContext(run_id="probe", suite_id="probe", timeout_s=30.0)
    responses: list[AgentResponse] = []

    for msg in PROBE_MESSAGES:
        try:
            resp = await adapter.invoke([Turn(role="user", content=msg)], ctx)
            responses.append(resp)
        except Exception:
            responses.append(AgentResponse(
                output="", tool_calls=[], retrieved_contexts=[],
                latency_ms=0, token_usage=__import__("harness.adapters.types", fromlist=["TokenUsage"]).TokenUsage(0, 0),
                raw_events=[],
            ))

    capabilities = classify_capabilities(responses)
    return capabilities, responses
```

Actually, the prober has a bad import pattern. Let me fix:

```python
# backend/src/harness/detection/prober.py
from harness.adapters.http_agent import HTTPAgentAdapter
from harness.adapters.types import AgentResponse, RunContext, TokenUsage, Turn
from harness.detection.classifier import classify_capabilities

PROBE_MESSAGES = [
    "What can you help me with? What are your capabilities?",
    "What is 15 * 23 + 7?",
    "Based on your knowledge base, what information do you have available?",
]


async def probe_agent(
    endpoint_url: str,
    auth_header: str | None = None,
    schema_type: str = "openai",
) -> tuple[set[str], list[AgentResponse]]:
    """Probe an agent endpoint to detect capabilities.

    Returns (detected_capabilities, probe_responses).
    """
    adapter = HTTPAgentAdapter(
        endpoint_url=endpoint_url,
        auth_header=auth_header,
        schema_type=schema_type,
        detected_capabilities={"text"},
    )

    ctx = RunContext(run_id="probe", suite_id="probe", timeout_s=30.0)
    responses: list[AgentResponse] = []

    for msg in PROBE_MESSAGES:
        try:
            resp = await adapter.invoke([Turn(role="user", content=msg)], ctx)
            responses.append(resp)
        except Exception:
            responses.append(AgentResponse(
                output="", tool_calls=[], retrieved_contexts=[],
                latency_ms=0, token_usage=TokenUsage(input_tokens=0, output_tokens=0),
                raw_events=[],
            ))

    capabilities = classify_capabilities(responses)
    return capabilities, responses
```

- [ ] **Step 7: Run all detection tests**

```bash
cd backend && uv run pytest tests/unit/test_classifier.py tests/unit/test_prober.py -v
```

- [ ] **Step 8: Commit**

```bash
git add backend/src/harness/detection/ backend/tests/unit/test_classifier.py backend/tests/unit/test_prober.py
git commit -m "feat: add agent capability auto-detection (prober + classifier)"
```

---

## Task 5: Grader (Letter Grade Calculation)

**Files:**
- Create: `backend/src/harness/eval/grader.py`
- Create: `backend/tests/unit/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/unit/test_grader.py
from harness.eval.grader import calculate_grade, GradeResult


def test_grade_a() -> None:
    result = calculate_grade({"m1": 0.95, "m2": 0.92})
    assert result.letter == "A"
    assert result.score == 93.5


def test_grade_b() -> None:
    result = calculate_grade({"m1": 0.85, "m2": 0.80})
    assert result.letter == "B"


def test_grade_c() -> None:
    result = calculate_grade({"m1": 0.75, "m2": 0.72})
    assert result.letter == "C"


def test_grade_d() -> None:
    result = calculate_grade({"m1": 0.65, "m2": 0.60})
    assert result.letter == "D"


def test_grade_f() -> None:
    result = calculate_grade({"m1": 0.40, "m2": 0.50})
    assert result.letter == "F"


def test_grade_empty_scores() -> None:
    result = calculate_grade({})
    assert result.letter == "F"
    assert result.score == 0.0


def test_grade_perfect() -> None:
    result = calculate_grade({"m1": 1.0, "m2": 1.0, "m3": 1.0})
    assert result.letter == "A"
    assert result.score == 100.0
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && uv run pytest tests/unit/test_grader.py -v
```

- [ ] **Step 3: Implement grader**

```python
# backend/src/harness/eval/grader.py
from dataclasses import dataclass


@dataclass(frozen=True)
class GradeResult:
    letter: str
    score: float  # 0-100


def calculate_grade(metric_averages: dict[str, float]) -> GradeResult:
    """Calculate a letter grade from metric average scores.

    Scores are 0.0-1.0 floats. Grade is based on the mean of all scores.
    """
    if not metric_averages:
        return GradeResult(letter="F", score=0.0)

    mean = sum(metric_averages.values()) / len(metric_averages)
    score = round(mean * 100, 1)

    if score >= 90:
        letter = "A"
    elif score >= 80:
        letter = "B"
    elif score >= 70:
        letter = "C"
    elif score >= 60:
        letter = "D"
    else:
        letter = "F"

    return GradeResult(letter=letter, score=score)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/unit/test_grader.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/eval/grader.py backend/tests/unit/test_grader.py
git commit -m "feat: add letter grade calculator for eval reports"
```

---

## Task 6: Quick Eval Orchestrator

**Files:**
- Create: `backend/src/harness/eval/quick_eval.py`
- Create: `backend/tests/integration/test_quick_eval.py`

- [ ] **Step 1: Implement quick eval orchestrator**

```python
# backend/src/harness/eval/quick_eval.py
import uuid
from dataclasses import dataclass
from typing import Any

from harness.adapters.http_agent import HTTPAgentAdapter
from harness.adapters.types import ToolCall, Turn
from harness.detection.classifier import classify_capabilities
from harness.detection.prober import probe_agent
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.eval.grader import GradeResult, calculate_grade
from harness.eval.metrics import MetricBackend, MetricConfig
from harness.eval.report import EvalReport


CAPABILITY_METRICS: dict[str, list[MetricConfig]] = {
    "text": [
        MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
    ],
    "tools": [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=0.8),
        MetricConfig(name="final_response_match_v2", backend=MetricBackend.ADK, threshold=0.7),
    ],
    "rag": [
        MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
        MetricConfig(name="contextual_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
        MetricConfig(name="hallucination", backend=MetricBackend.DEEPEVAL, threshold=0.8),
    ],
}

QUICK_TEST_CASES = [
    {"input": "What can you help me with?", "tags": ["general"]},
    {"input": "What is the capital of France?", "tags": ["knowledge"]},
    {"input": "Summarize your main capabilities in one sentence.", "tags": ["general"]},
    {"input": "What is 25 * 4?", "tags": ["math"]},
    {"input": "Explain what you do in simple terms.", "tags": ["general"]},
]


@dataclass
class QuickEvalResult:
    run_id: str
    grade: GradeResult
    report: EvalReport
    capabilities: set[str]
    summary: dict[str, Any]


async def run_quick_eval(
    endpoint_url: str,
    capabilities: set[str],
    auth_header: str | None = None,
    num_cases: int = 5,
) -> QuickEvalResult:
    """Run a quick eval against an external agent endpoint."""
    adapter = HTTPAgentAdapter(
        endpoint_url=endpoint_url,
        auth_header=auth_header,
        detected_capabilities=capabilities,
    )

    # Select metrics based on capabilities
    metrics: list[MetricConfig] = []
    for cap in capabilities:
        metrics.extend(CAPABILITY_METRICS.get(cap, []))

    # Build test cases
    test_cases = [
        EvalTestCase(
            id=f"quick-{i}",
            input=[Turn(role="user", content=tc["input"])],
            expected_output=None,
            expected_tools=None,
            reference_contexts=None,
            tags=tc["tags"],
        )
        for i, tc in enumerate(QUICK_TEST_CASES[:num_cases])
    ]

    run_id = str(uuid.uuid4())
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id=run_id, suite_id="quick-eval")

    summary = report.summary()
    grade = calculate_grade(summary.get("metric_averages", {}))

    return QuickEvalResult(
        run_id=run_id,
        grade=grade,
        report=report,
        capabilities=capabilities,
        summary=summary,
    )
```

- [ ] **Step 2: Write integration test**

```python
# backend/tests/integration/test_quick_eval.py
import json
import pytest
from unittest.mock import AsyncMock, patch

from harness.eval.quick_eval import run_quick_eval, CAPABILITY_METRICS


@pytest.mark.asyncio
async def test_quick_eval_with_mock_agent() -> None:
    mock_response = {
        "choices": [{"message": {"role": "assistant", "content": "I can help with general questions."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }

    with patch("harness.adapters.http_agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_resp = AsyncMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = lambda: None
        mock_client.post.return_value = mock_resp

        result = await run_quick_eval(
            endpoint_url="https://mock-agent.com/v1/chat/completions",
            capabilities={"text"},
            num_cases=2,
        )

        assert result.run_id is not None
        assert result.grade.letter in ("A", "B", "C", "D", "F")
        assert len(result.report.case_results) == 2
        assert result.capabilities == {"text"}
```

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest tests/integration/test_quick_eval.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/harness/eval/quick_eval.py backend/tests/integration/test_quick_eval.py
git commit -m "feat: add quick eval orchestrator (detect → eval → grade)"
```

---

## Task 7: Quick Eval REST API + Meta-Agent Tools

**Files:**
- Create: `backend/src/harness/api/quick_eval_routes.py`
- Create: `backend/src/harness/meta_tools/connect_agent.py`
- Create: `backend/src/harness/meta_tools/quick_eval_tool.py`
- Modify: `backend/src/harness/agents/meta_agent.py`
- Modify: `backend/src/harness/main.py`

- [ ] **Step 1: Create REST endpoints**

```python
# backend/src/harness/api/quick_eval_routes.py
import json

from fastapi import APIRouter
from pydantic import BaseModel

from harness.detection.prober import probe_agent
from harness.eval.quick_eval import run_quick_eval

router = APIRouter(prefix="/api", tags=["quick-eval"])


class ProbeRequest(BaseModel):
    endpoint_url: str
    auth_header: str | None = None
    schema_type: str = "openai"


class ProbeResponse(BaseModel):
    reachable: bool
    detected_capabilities: list[str]
    error: str | None = None


class QuickEvalRequest(BaseModel):
    endpoint_url: str
    auth_header: str | None = None
    capabilities: list[str]
    num_cases: int = 5


class QuickEvalResponse(BaseModel):
    run_id: str
    grade_letter: str
    grade_score: float
    pass_rate: float
    total_cases: int
    passed: int
    failed: int
    avg_latency_ms: float
    metric_averages: dict[str, float]
    results: list[dict]


@router.post("/probe", response_model=ProbeResponse)
async def probe_endpoint(req: ProbeRequest) -> ProbeResponse:
    try:
        capabilities, _ = await probe_agent(
            endpoint_url=req.endpoint_url,
            auth_header=req.auth_header,
            schema_type=req.schema_type,
        )
        return ProbeResponse(reachable=True, detected_capabilities=sorted(capabilities))
    except Exception as e:
        return ProbeResponse(reachable=False, detected_capabilities=[], error=str(e))


@router.post("/quick-eval", response_model=QuickEvalResponse)
async def quick_eval_endpoint(req: QuickEvalRequest) -> QuickEvalResponse:
    result = await run_quick_eval(
        endpoint_url=req.endpoint_url,
        capabilities=set(req.capabilities),
        auth_header=req.auth_header,
        num_cases=req.num_cases,
    )
    summary = result.summary
    case_results = [
        {
            "test_case_id": cr.test_case_id,
            "passed": cr.passed,
            "latency_ms": round(cr.latency_ms, 1),
            "metrics": [
                {"name": mr.name, "score": round(mr.score, 3), "passed": mr.passed, "threshold": mr.threshold}
                for mr in cr.metric_results
            ],
        }
        for cr in result.report.case_results
    ]
    return QuickEvalResponse(
        run_id=result.run_id,
        grade_letter=result.grade.letter,
        grade_score=result.grade.score,
        pass_rate=summary.get("pass_rate", 0),
        total_cases=summary.get("total_cases", 0),
        passed=summary.get("passed", 0),
        failed=summary.get("failed", 0),
        avg_latency_ms=summary.get("avg_latency_ms", 0),
        metric_averages=summary.get("metric_averages", {}),
        results=case_results,
    )
```

- [ ] **Step 2: Create meta-agent tools**

```python
# backend/src/harness/meta_tools/connect_agent.py
import json
from harness.detection.prober import probe_agent


async def connect_agent(endpoint_url: str, auth_header: str = "") -> str:
    """Connect to an external agent endpoint and detect its capabilities.

    Args:
        endpoint_url: The agent's HTTP endpoint URL (OpenAI-compatible format).
        auth_header: Optional authorization header value (e.g., "Bearer sk-...").

    Returns:
        JSON with detected capabilities and reachability status.
    """
    try:
        capabilities, responses = await probe_agent(
            endpoint_url=endpoint_url,
            auth_header=auth_header or None,
        )
        return json.dumps({
            "reachable": True,
            "endpoint_url": endpoint_url,
            "detected_capabilities": sorted(capabilities),
            "probe_summary": [
                {"probe": i + 1, "response_length": len(r.output), "tool_calls": len(r.tool_calls)}
                for i, r in enumerate(responses)
            ],
            "message": f"Agent detected with capabilities: {', '.join(sorted(capabilities))}. Confirm these before running eval.",
        }, indent=2)
    except Exception as e:
        return json.dumps({"reachable": False, "error": str(e)})
```

```python
# backend/src/harness/meta_tools/quick_eval_tool.py
import json
from harness.eval.quick_eval import run_quick_eval


async def quick_eval(endpoint_url: str, capabilities: str, auth_header: str = "", num_cases: int = 5) -> str:
    """Run a quick evaluation against an external agent endpoint.

    Args:
        endpoint_url: The agent's HTTP endpoint URL.
        capabilities: Comma-separated capabilities (e.g., "text,tools,rag").
        auth_header: Optional authorization header.
        num_cases: Number of test cases to run (default 5, max 10).

    Returns:
        JSON with grade, scores, and per-case results.
    """
    caps = {c.strip() for c in capabilities.split(",") if c.strip()}
    num_cases = min(num_cases, 10)

    try:
        result = await run_quick_eval(
            endpoint_url=endpoint_url,
            capabilities=caps,
            auth_header=auth_header or None,
            num_cases=num_cases,
        )
        case_results = [
            {"test_case_id": cr.test_case_id, "passed": cr.passed, "latency_ms": round(cr.latency_ms, 1),
             "metrics": [{"name": mr.name, "score": round(mr.score, 3), "passed": mr.passed} for mr in cr.metric_results]}
            for cr in result.report.case_results
        ]
        return json.dumps({
            "run_id": result.run_id,
            "grade": result.grade.letter,
            "score": result.grade.score,
            "summary": result.summary,
            "results": case_results,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Quick eval failed: {e}"})
```

- [ ] **Step 3: Update meta_agent.py**

Read `backend/src/harness/agents/meta_agent.py` and add:

```python
from harness.meta_tools.connect_agent import connect_agent
from harness.meta_tools.quick_eval_tool import quick_eval
```

Add to tools list: `connect_agent, quick_eval`

Add to META_AGENT_INSTRUCTION:
```
9. Connect external agent endpoints (use connect_agent)
10. Run quick evaluations on external agents (use quick_eval)

For external agents, guide users through: connect_agent (paste URL) → confirm capabilities → quick_eval.
```

- [ ] **Step 4: Update main.py to include quick eval routes**

Add import and include router:
```python
from harness.api.quick_eval_routes import router as quick_eval_router
# in create_app():
app.include_router(quick_eval_router)
```

- [ ] **Step 5: Run existing tests**

```bash
cd backend && uv run pytest tests/e2e/test_health.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/harness/api/quick_eval_routes.py backend/src/harness/meta_tools/connect_agent.py backend/src/harness/meta_tools/quick_eval_tool.py backend/src/harness/agents/meta_agent.py backend/src/harness/main.py
git commit -m "feat: add quick eval REST API and meta-agent tools"
```

---

## Task 8: Frontend — Quick Eval Page + Report Card

**Files:**
- Create: `frontend/src/app/quick-eval/page.tsx`
- Create: `frontend/src/components/report-card.tsx`
- Create: `frontend/src/components/case-detail.tsx`

- [ ] **Step 1: Create report card component**

```tsx
// frontend/src/components/report-card.tsx
"use client";

interface ReportCardProps {
  gradeLetter: string;
  gradeScore: number;
  passRate: number;
  totalCases: number;
  passed: number;
  failed: number;
  avgLatencyMs: number;
  metricAverages: Record<string, number>;
}

const gradeColors: Record<string, string> = {
  A: "text-green-400 border-green-400",
  B: "text-blue-400 border-blue-400",
  C: "text-yellow-400 border-yellow-400",
  D: "text-orange-400 border-orange-400",
  F: "text-red-400 border-red-400",
};

export function ReportCard({
  gradeLetter, gradeScore, passRate, totalCases, passed, failed, avgLatencyMs, metricAverages,
}: ReportCardProps) {
  const color = gradeColors[gradeLetter] || "text-gray-400 border-gray-400";

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-lg">
      <div className="flex items-center gap-4 mb-4">
        <div className={`text-5xl font-bold border-2 rounded-lg px-4 py-2 ${color}`}>
          {gradeLetter}
        </div>
        <div>
          <p className="text-2xl font-semibold text-white">{gradeScore}%</p>
          <p className="text-sm text-gray-400">Agent Quality Score</p>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        {Object.entries(metricAverages).map(([name, score]) => (
          <div key={name} className="flex items-center gap-2">
            <span className="text-xs text-gray-400 w-40 truncate">{name}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${score >= 0.8 ? "bg-green-500" : score >= 0.6 ? "bg-yellow-500" : "bg-red-500"}`}
                style={{ width: `${Math.round(score * 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-300 w-10 text-right">{Math.round(score * 100)}%</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-sm">
        <div className="bg-gray-800 rounded p-2">
          <p className="text-white font-medium">{passed}/{totalCases}</p>
          <p className="text-gray-500 text-xs">Pass Rate</p>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <p className="text-white font-medium">{Math.round(avgLatencyMs)}ms</p>
          <p className="text-gray-500 text-xs">Avg Latency</p>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <p className={`font-medium ${failed > 0 ? "text-red-400" : "text-green-400"}`}>{failed}</p>
          <p className="text-gray-500 text-xs">Failures</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create case detail component**

```tsx
// frontend/src/components/case-detail.tsx
"use client";

import { useState } from "react";

interface MetricScore {
  name: string;
  score: number;
  passed: boolean;
  threshold: number;
}

interface CaseResult {
  test_case_id: string;
  passed: boolean;
  latency_ms: number;
  metrics: MetricScore[];
}

export function CaseDetail({ results }: { results: CaseResult[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="space-y-2 mt-4">
      <h3 className="text-sm font-medium text-gray-400">Test Cases</h3>
      {results.map((r) => (
        <div key={r.test_case_id} className="bg-gray-900 border border-gray-700 rounded">
          <button
            className="w-full flex items-center justify-between p-3 text-left"
            onClick={() => setExpanded(expanded === r.test_case_id ? null : r.test_case_id)}
          >
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded ${r.passed ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                {r.passed ? "PASS" : "FAIL"}
              </span>
              <span className="text-sm text-gray-300 font-mono">{r.test_case_id}</span>
            </div>
            <span className="text-xs text-gray-500">{Math.round(r.latency_ms)}ms</span>
          </button>
          {expanded === r.test_case_id && (
            <div className="px-3 pb-3 space-y-1">
              {r.metrics.map((m) => (
                <div key={m.name} className="flex items-center gap-2 text-xs">
                  <span className={m.passed ? "text-green-400" : "text-red-400"}>
                    {m.passed ? "✓" : "✗"}
                  </span>
                  <span className="text-gray-400">{m.name}:</span>
                  <span className="text-gray-200">{(m.score * 100).toFixed(1)}%</span>
                  <span className="text-gray-600">(threshold: {(m.threshold * 100).toFixed(0)}%)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create Quick Eval page**

```tsx
// frontend/src/app/quick-eval/page.tsx
"use client";

import { useState } from "react";
import { ReportCard } from "@/components/report-card";
import { CaseDetail } from "@/components/case-detail";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Step = "input" | "probing" | "confirm" | "running" | "done";

export default function QuickEvalPage() {
  const [step, setStep] = useState<Step>("input");
  const [url, setUrl] = useState("");
  const [authHeader, setAuthHeader] = useState("");
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleProbe() {
    setStep("probing");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/probe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint_url: url, auth_header: authHeader || null }),
      });
      const data = await res.json();
      if (!data.reachable) {
        setError(data.error || "Agent not reachable");
        setStep("input");
        return;
      }
      setCapabilities(data.detected_capabilities);
      setStep("confirm");
    } catch (e: any) {
      setError(e.message);
      setStep("input");
    }
  }

  async function handleEval() {
    setStep("running");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/quick-eval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint_url: url,
          auth_header: authHeader || null,
          capabilities,
          num_cases: 5,
        }),
      });
      const data = await res.json();
      setResult(data);
      setStep("done");
    } catch (e: any) {
      setError(e.message);
      setStep("confirm");
    }
  }

  function toggleCapability(cap: string) {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap]
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        <h1 className="text-3xl font-bold text-white mb-2">Quick Eval</h1>
        <p className="text-gray-400 mb-8">Paste your agent endpoint. Get a quality report in 2 minutes.</p>

        {error && (
          <div className="bg-red-900/50 border border-red-700 rounded p-3 mb-4 text-red-300 text-sm">{error}</div>
        )}

        {step === "input" && (
          <div className="space-y-4">
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
              placeholder="https://your-agent.com/v1/chat/completions"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <input
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
              placeholder="Bearer sk-... (optional)"
              value={authHeader}
              onChange={(e) => setAuthHeader(e.target.value)}
            />
            <button
              className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-medium disabled:opacity-50"
              onClick={handleProbe}
              disabled={!url}
            >
              Scan Agent
            </button>
          </div>
        )}

        {step === "probing" && (
          <div className="text-center py-8">
            <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">Probing agent capabilities...</p>
          </div>
        )}

        {step === "confirm" && (
          <div className="space-y-4">
            <p className="text-gray-300">Detected capabilities — confirm or adjust:</p>
            <div className="flex gap-2 flex-wrap">
              {["text", "tools", "rag"].map((cap) => (
                <button
                  key={cap}
                  className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                    capabilities.includes(cap)
                      ? "bg-blue-600 border-blue-500 text-white"
                      : "bg-gray-900 border-gray-700 text-gray-400 hover:border-gray-500"
                  }`}
                  onClick={() => toggleCapability(cap)}
                >
                  {cap}
                </button>
              ))}
            </div>
            <button
              className="w-full bg-green-600 hover:bg-green-700 text-white rounded-lg py-3 font-medium"
              onClick={handleEval}
            >
              Run Eval
            </button>
          </div>
        )}

        {step === "running" && (
          <div className="text-center py-8">
            <div className="animate-spin h-8 w-8 border-2 border-green-500 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">Running evaluation...</p>
          </div>
        )}

        {step === "done" && result && (
          <div>
            <ReportCard
              gradeLetter={result.grade_letter}
              gradeScore={result.grade_score}
              passRate={result.pass_rate}
              totalCases={result.total_cases}
              passed={result.passed}
              failed={result.failed}
              avgLatencyMs={result.avg_latency_ms}
              metricAverages={result.metric_averages}
            />
            <CaseDetail results={result.results} />
            <button
              className="mt-4 w-full bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm"
              onClick={() => { setStep("input"); setResult(null); }}
            >
              Evaluate Another Agent
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add NEXT_PUBLIC_API_URL to .env.local**

```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> frontend/.env.local
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/quick-eval/ frontend/src/components/report-card.tsx frontend/src/components/case-detail.tsx frontend/.env.local.example
git commit -m "feat: add Quick Eval page with report card and case details"
```

---

## Task Summary

| Task | What | Files |
|---|---|---|
| 1 | Crypto helpers + encryption config | `crypto.py`, `config.py` |
| 2 | Data model (org_id, UserSettings, ConnectedAgent) | `models.py` |
| 3 | HTTPAgentAdapter | `http_agent.py` |
| 4 | Auto-detection (prober + classifier) | `detection/` |
| 5 | Letter grade calculator | `grader.py` |
| 6 | Quick eval orchestrator | `quick_eval.py` |
| 7 | REST API + meta-agent tools | `quick_eval_routes.py`, `connect_agent.py`, `quick_eval_tool.py` |
| 8 | Frontend (Quick Eval page + Report Card) | `quick-eval/page.tsx`, `report-card.tsx`, `case-detail.tsx` |
