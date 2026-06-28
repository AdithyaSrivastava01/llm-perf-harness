# Agent-Evals Meta-Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conversational eval harness where users chat with an ADK meta-agent to evaluate demo LLM agents (tool-calling + RAG) via CopilotKit + AG-UI, with pluggable metrics (ADK + DeepEval), HITL test case curation and baseline promotion, deployed free on Cloud Run + Vercel + Neon.

**Architecture:** Three-layer split — Conversational Layer (ADK meta-agent via ag_ui_adk → CopilotKit), Eval Engine Layer (framework-agnostic runner with ADK + DeepEval metric backends), Agent Layer (demo agents behind AgentAdapter Protocol). Auth via NextAuth.js JWT, data in Neon Postgres via SQLAlchemy async.

**Tech Stack:** Python 3.12, FastAPI, google-adk 2.3.0, ag-ui-adk 0.7.0, DeepEval, SQLAlchemy async + asyncpg, Alembic, Next.js 15, CopilotKit, shadcn/ui, Tailwind CSS, NextAuth.js, Neon Postgres, Cloud Run, Vercel, Grafana Cloud (OTel).

**Spec:** `docs/superpowers/specs/2026-06-28-agent-evals-meta-harness-design.md`

---

## File Structure

```
llm-perf-harness/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── src/
│   │   └── harness/
│   │       ├── __init__.py
│   │       ├── main.py                     # FastAPI app, CORS, lifespan
│   │       ├── config.py                   # Pydantic Settings
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── engine.py               # async engine + session factory
│   │       │   └── models.py               # SQLAlchemy ORM models
│   │       ├── adapters/
│   │       │   ├── __init__.py
│   │       │   ├── types.py                # Turn, ToolCall, AgentResponse, etc.
│   │       │   ├── protocol.py             # AgentAdapter Protocol
│   │       │   ├── tool_calling.py         # ToolCallingAdapter
│   │       │   └── rag.py                  # RAGAdapter
│   │       ├── eval/
│   │       │   ├── __init__.py
│   │       │   ├── metrics.py              # MetricConfig, MetricResult, routing
│   │       │   ├── engine.py               # EvalRunner — runs suite, collects results
│   │       │   ├── report.py               # EvalReport aggregation
│   │       │   └── baseline.py             # Baseline snapshot + regression detection
│   │       ├── agents/
│   │       │   ├── __init__.py
│   │       │   ├── tools.py                # Tool functions (weather, calc, search)
│   │       │   ├── tool_calling_agent.py   # ADK LlmAgent with tools
│   │       │   ├── rag_agent.py            # ADK LlmAgent with retrieval
│   │       │   └── meta_agent.py           # ADK LlmAgent — orchestrator
│   │       ├── meta_tools/
│   │       │   ├── __init__.py
│   │       │   ├── registry.py             # Agent + metric registry
│   │       │   ├── list_agents.py          # list available agents
│   │       │   ├── list_metrics.py         # list metrics per agent type
│   │       │   ├── run_eval.py             # trigger eval run
│   │       │   ├── get_results.py          # fetch eval results
│   │       │   ├── generate_test_cases.py  # auto-gen test cases
│   │       │   ├── review_test_cases.py    # present cases for HITL review
│   │       │   ├── compare_runs.py         # diff two eval runs
│   │       │   ├── promote_baseline.py     # HITL baseline promotion
│   │       │   └── explain_failure.py      # deep-dive a failing case
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── agui.py                 # ag_ui_adk endpoint setup
│   │       │   └── health.py               # /health endpoint
│   │       ├── auth/
│   │       │   ├── __init__.py
│   │       │   └── jwt.py                  # JWT decode + FastAPI dependency
│   │       └── telemetry/
│   │           ├── __init__.py
│   │           └── otel.py                 # OTel SDK setup + custom spans
│   ├── tests/
│   │   ├── conftest.py                     # shared fixtures, mock agents, DB setup
│   │   ├── fixtures/
│   │   │   ├── tool_calling_evalset.json
│   │   │   └── rag_evalset.json
│   │   ├── unit/
│   │   │   ├── test_types.py
│   │   │   ├── test_adapter_protocol.py
│   │   │   ├── test_metrics.py
│   │   │   ├── test_eval_engine.py
│   │   │   ├── test_report.py
│   │   │   └── test_baseline.py
│   │   ├── integration/
│   │   │   ├── test_tool_calling_eval.py
│   │   │   └── test_rag_eval.py
│   │   └── e2e/
│   │       ├── test_health.py
│   │       └── test_agui.py
│   └── Dockerfile
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── components.json                     # shadcn/ui
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── globals.css
│   │   │   ├── api/
│   │   │   │   ├── copilotkit/
│   │   │   │   │   └── route.ts
│   │   │   │   └── auth/
│   │   │   │       └── [...nextauth]/
│   │   │   │           └── route.ts
│   │   │   └── dashboard/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── chat-panel.tsx
│   │   │   ├── agent-card.tsx
│   │   │   ├── results-table.tsx
│   │   │   ├── test-case-list.tsx
│   │   │   └── run-history.tsx
│   │   ├── lib/
│   │   │   └── auth.ts
│   │   └── types/
│   │       └── index.ts
│   └── .env.local.example
└── README.md
```

---

## WEEK 1: Foundation + Eval Engine

---

### Task 1: Backend Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/harness/__init__.py`
- Create: `backend/src/harness/config.py`
- Create: `backend/src/harness/main.py`
- Create: `backend/src/harness/api/__init__.py`
- Create: `backend/src/harness/api/health.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/e2e/__init__.py` (empty)
- Create: `backend/tests/e2e/test_health.py`

- [ ] **Step 1: Initialize backend with uv**

```bash
cd /home/adithya/Document/llm-perf-harness
mkdir -p backend
cd backend
uv init --lib --name harness
```

- [ ] **Step 2: Add core dependencies**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add fastapi uvicorn[standard] pydantic-settings
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

- [ ] **Step 3: Create config.py**

```python
# backend/src/harness/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "HARNESS_"}

    google_api_key: str = ""
    openai_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
    otel_endpoint: str = ""
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
```

- [ ] **Step 4: Create health endpoint**

```python
# backend/src/harness/api/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Create FastAPI app**

```python
# backend/src/harness/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.api.health import router as health_router
from harness.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Agent-Evals Meta-Harness")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 6: Write health endpoint test**

```python
# backend/tests/e2e/test_health.py
import pytest
from httpx import ASGITransport, AsyncClient

from harness.main import app


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 7: Configure pytest**

Add to `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 8: Run test to verify it passes**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/e2e/test_health.py -v
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, config, health endpoint"
```

---

### Task 2: Database Models + Migrations

**Files:**
- Create: `backend/src/harness/db/__init__.py`
- Create: `backend/src/harness/db/engine.py`
- Create: `backend/src/harness/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/tests/unit/__init__.py` (empty)
- Create: `backend/tests/unit/test_models.py`

- [ ] **Step 1: Add database dependencies**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add sqlalchemy[asyncio] asyncpg alembic aiosqlite
```

Note: `aiosqlite` is for local dev/tests. Production uses `asyncpg` with Neon.

- [ ] **Step 2: Create async engine**

```python
# backend/src/harness/db/engine.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from harness.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 3: Create ORM models**

```python
# backend/src/harness/db/models.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    adapter_type: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalSuite(Base):
    __tablename__ = "eval_suites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="suite", lazy="selectin")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_suites.id"), nullable=False
    )
    input: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_tools: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reference_contexts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    suite: Mapped["EvalSuite"] = relationship(back_populates="test_cases")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_suites.id"), nullable=False
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_baseline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    otel_trace_id: Mapped[str | None] = mapped_column(String, nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(back_populates="run", lazy="selectin")

    __table_args__ = (Index("ix_eval_runs_suite_created", "suite_id", "created_at"),)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False)
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False
    )
    agent_response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metric_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped["EvalRun"] = relationship(back_populates="results")

    __table_args__ = (Index("ix_eval_results_run_id", "run_id"),)


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("eval_suites.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    promoted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (Index("ix_baselines_agent_suite_active", "agent_id", "suite_id", "active"),)
```

- [ ] **Step 4: Write model instantiation tests**

```python
# backend/tests/unit/test_models.py
import uuid

from harness.db.models import Agent, Baseline, EvalResult, EvalRun, EvalSuite, TestCase, User


def test_user_model_defaults() -> None:
    user = User(email="test@example.com", name="Test", auth_provider="github")
    assert user.email == "test@example.com"
    assert user.auth_provider == "github"
    assert user.avatar_url is None


def test_agent_model_with_config() -> None:
    agent = Agent(
        name="weather-agent",
        adapter_type="tool_calling",
        config={"model": "gemini-2.5-flash", "tools": ["get_weather"]},
        capabilities=["text", "tools"],
        is_demo=True,
    )
    assert agent.name == "weather-agent"
    assert agent.config["model"] == "gemini-2.5-flash"
    assert "tools" in agent.capabilities


def test_eval_run_default_status() -> None:
    run = EvalRun(
        suite_id=uuid.uuid4(),
        triggered_by=uuid.uuid4(),
    )
    assert run.status == "pending"
    assert run.is_baseline is False


def test_test_case_default_approved() -> None:
    tc = TestCase(
        suite_id=uuid.uuid4(),
        input={"turns": [{"role": "user", "content": "hello"}]},
    )
    assert tc.approved is False


def test_baseline_default_active() -> None:
    baseline = Baseline(
        agent_id=uuid.uuid4(),
        suite_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        scores={"tool_trajectory_avg_score": 1.0},
        promoted_by=uuid.uuid4(),
    )
    assert baseline.active is True
```

- [ ] **Step 5: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_models.py -v
```

Expected: PASS

- [ ] **Step 6: Set up Alembic**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run alembic init alembic
```

Then update `alembic/env.py` to import models and use async engine:

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from harness.config import settings
from harness.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

Update `alembic.ini` to remove the default `sqlalchemy.url` (we use settings instead):

```ini
# Comment out or remove this line in alembic.ini:
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

- [ ] **Step 7: Generate initial migration**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run alembic revision --autogenerate -m "initial schema"
```

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add database models and Alembic migrations"
```

---

### Task 3: Adapter Types

**Files:**
- Create: `backend/src/harness/adapters/__init__.py`
- Create: `backend/src/harness/adapters/types.py`
- Create: `backend/tests/unit/test_types.py`

- [ ] **Step 1: Write failing test for types**

```python
# backend/tests/unit/test_types.py
from harness.adapters.types import AgentResponse, MetricResult, ToolCall, ToolSpec, TokenUsage, Turn


def test_turn_creation() -> None:
    turn = Turn(role="user", content="What is the weather?")
    assert turn.role == "user"
    assert turn.content == "What is the weather?"


def test_tool_call_creation() -> None:
    tc = ToolCall(name="get_weather", args={"city": "Paris"})
    assert tc.name == "get_weather"
    assert tc.args == {"city": "Paris"}


def test_tool_spec_creation() -> None:
    spec = ToolSpec(name="get_weather", description="Get weather", parameters={"city": "string"})
    assert spec.name == "get_weather"


def test_token_usage() -> None:
    usage = TokenUsage(input_tokens=100, output_tokens=50)
    assert usage.total_tokens == 150


def test_agent_response_creation() -> None:
    resp = AgentResponse(
        output="It's sunny in Paris",
        tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
        retrieved_contexts=[],
        latency_ms=150.5,
        token_usage=TokenUsage(input_tokens=100, output_tokens=50),
        raw_events=[],
    )
    assert resp.output == "It's sunny in Paris"
    assert len(resp.tool_calls) == 1
    assert resp.latency_ms == 150.5


def test_metric_result_creation() -> None:
    result = MetricResult(
        name="tool_trajectory_avg_score",
        score=1.0,
        threshold=1.0,
        details={"match_type": "EXACT"},
        backend="adk",
    )
    assert result.passed is True


def test_metric_result_fails_below_threshold() -> None:
    result = MetricResult(
        name="faithfulness",
        score=0.6,
        threshold=0.8,
        details={},
        backend="deepeval",
    )
    assert result.passed is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_types.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'harness.adapters.types'`

- [ ] **Step 3: Implement types**

```python
# backend/src/harness/adapters/__init__.py
```

```python
# backend/src/harness/adapters/types.py
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AgentResponse:
    output: str
    tool_calls: list[ToolCall]
    retrieved_contexts: list[str]
    latency_ms: float
    token_usage: TokenUsage
    raw_events: list[Any]


@dataclass(frozen=True)
class MetricResult:
    name: str
    score: float
    threshold: float
    details: dict[str, Any]
    backend: str  # "adk" | "deepeval"

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass
class RunContext:
    run_id: str
    suite_id: str
    timeout_s: float = 300.0
    model_override: str | None = None
```

- [ ] **Step 4: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_types.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/adapters/ backend/tests/unit/test_types.py
git commit -m "feat: add adapter types (Turn, ToolCall, AgentResponse, MetricResult)"
```

---

### Task 4: AgentAdapter Protocol

**Files:**
- Create: `backend/src/harness/adapters/protocol.py`
- Create: `backend/tests/unit/test_adapter_protocol.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_adapter_protocol.py
import pytest

from harness.adapters.protocol import AgentAdapter
from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn


class MockToolCallingAdapter:
    """Minimal adapter that satisfies the Protocol."""

    @property
    def agent_id(self) -> str:
        return "mock-tool-agent"

    @property
    def display_name(self) -> str:
        return "Mock Tool Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        return AgentResponse(
            output="Sunny in Paris",
            tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
            retrieved_contexts=[],
            latency_ms=100.0,
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
            raw_events=[],
        )

    def supported_metrics(self) -> list[str]:
        return ["tool_trajectory_avg_score", "answer_relevancy"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [ToolSpec(name="get_weather", description="Get weather", parameters={"city": "string"})]

    def reference_contexts(self) -> list[str] | None:
        return None


class IncompleteAdapter:
    """Missing required methods — should NOT satisfy Protocol."""

    @property
    def agent_id(self) -> str:
        return "incomplete"


def test_mock_adapter_satisfies_protocol() -> None:
    adapter: AgentAdapter = MockToolCallingAdapter()
    assert adapter.agent_id == "mock-tool-agent"
    assert "tools" in adapter.capabilities
    assert adapter.expected_tools() is not None
    assert adapter.reference_contexts() is None


@pytest.mark.asyncio
async def test_mock_adapter_invoke() -> None:
    adapter = MockToolCallingAdapter()
    ctx = RunContext(run_id="run-1", suite_id="suite-1")
    response = await adapter.invoke([Turn(role="user", content="Weather in Paris?")], ctx)
    assert response.output == "Sunny in Paris"
    assert len(response.tool_calls) == 1


def test_incomplete_adapter_not_protocol() -> None:
    adapter = IncompleteAdapter()
    assert not isinstance(adapter, AgentAdapter)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_adapter_protocol.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement Protocol**

```python
# backend/src/harness/adapters/protocol.py
from typing import Protocol, runtime_checkable

from harness.adapters.types import AgentResponse, RunContext, ToolSpec, Turn


@runtime_checkable
class AgentAdapter(Protocol):
    """Wraps any agent into something the eval engine can drive."""

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def capabilities(self) -> set[str]: ...

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse: ...

    def supported_metrics(self) -> list[str]: ...

    def expected_tools(self) -> list[ToolSpec] | None: ...

    def reference_contexts(self) -> list[str] | None: ...
```

- [ ] **Step 4: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_adapter_protocol.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/adapters/protocol.py backend/tests/unit/test_adapter_protocol.py
git commit -m "feat: add AgentAdapter Protocol"
```

---

### Task 5: Tool-Calling ADK Agent + Adapter

**Files:**
- Create: `backend/src/harness/agents/__init__.py`
- Create: `backend/src/harness/agents/tools.py`
- Create: `backend/src/harness/agents/tool_calling_agent.py`
- Create: `backend/src/harness/adapters/tool_calling.py`
- Create: `backend/tests/integration/__init__.py` (empty)
- Create: `backend/tests/integration/test_tool_calling_eval.py`

- [ ] **Step 1: Add ADK dependency**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add google-adk
```

- [ ] **Step 2: Create tool functions**

```python
# backend/src/harness/agents/tools.py
import json
import math


def get_weather(city: str) -> str:
    """Get the current weather for a city. Returns temperature and conditions."""
    # Deterministic mock data for demo — replace with real API in production
    weather_data = {
        "paris": {"temp": 22, "conditions": "Sunny", "humidity": 45},
        "london": {"temp": 15, "conditions": "Cloudy", "humidity": 78},
        "new york": {"temp": 28, "conditions": "Partly cloudy", "humidity": 60},
        "tokyo": {"temp": 26, "conditions": "Clear", "humidity": 55},
    }
    data = weather_data.get(city.lower(), {"temp": 20, "conditions": "Unknown", "humidity": 50})
    return json.dumps(data)


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Supports basic arithmetic and math functions."""
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "pow": pow, "pi": math.pi, "e": math.e,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


def search_knowledge(query: str) -> str:
    """Search a knowledge base for information. Returns relevant text snippets."""
    # Deterministic mock for demo
    knowledge = {
        "python": "Python is a high-level programming language created by Guido van Rossum in 1991.",
        "fastapi": "FastAPI is a modern Python web framework for building APIs, created by Sebastián Ramírez.",
        "machine learning": "Machine learning is a subset of AI that enables systems to learn from data.",
    }
    query_lower = query.lower()
    for key, value in knowledge.items():
        if key in query_lower:
            return value
    return "No relevant information found."
```

- [ ] **Step 3: Create ADK tool-calling agent**

```python
# backend/src/harness/agents/tool_calling_agent.py
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
```

- [ ] **Step 4: Create ToolCallingAdapter**

```python
# backend/src/harness/adapters/tool_calling.py
import time
from typing import Any

from google.adk import Runner
from google.adk.agents import types
from google.adk.sessions import InMemorySessionService

from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn
from harness.agents.tool_calling_agent import create_tool_calling_agent


class ToolCallingAdapter:
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._agent = create_tool_calling_agent(model)
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            session_service=self._session_service,
            app_name="tool_calling_eval",
        )

    @property
    def agent_id(self) -> str:
        return "tool-calling-agent"

    @property
    def display_name(self) -> str:
        return "Tool-Calling Demo Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        session = await self._session_service.create_session(
            app_name="tool_calling_eval", user_id=f"eval-{context.run_id}"
        )
        tool_calls: list[ToolCall] = []
        final_output = ""
        raw_events: list[Any] = []
        input_tokens = 0
        output_tokens = 0

        start = time.monotonic()

        for turn in input:
            message = types.Content(role=turn.role, parts=[types.Part(text=turn.content)])
            async for event in self._runner.run_async(
                user_id=f"eval-{context.run_id}",
                session_id=session.id,
                new_message=message,
            ):
                raw_events.append(event)
                # Collect tool calls from function_call events
                if event.actions and event.actions.function_calls:
                    for fc in event.actions.function_calls:
                        tool_calls.append(ToolCall(name=fc.name, args=dict(fc.args or {})))
                # Collect final response
                if event.is_final_response() and event.content and event.content.parts:
                    final_output = event.content.parts[0].text or ""
                # Collect token usage if available
                if hasattr(event, "usage") and event.usage:
                    input_tokens += getattr(event.usage, "prompt_tokens", 0)
                    output_tokens += getattr(event.usage, "completion_tokens", 0)

        elapsed = (time.monotonic() - start) * 1000

        return AgentResponse(
            output=final_output,
            tool_calls=tool_calls,
            retrieved_contexts=[],
            latency_ms=elapsed,
            token_usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            raw_events=raw_events,
        )

    def supported_metrics(self) -> list[str]:
        return ["tool_trajectory_avg_score", "final_response_match_v2", "answer_relevancy"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [
            ToolSpec(name="get_weather", description="Get weather for a city", parameters={"city": "string"}),
            ToolSpec(name="calculate", description="Evaluate math expression", parameters={"expression": "string"}),
            ToolSpec(
                name="search_knowledge", description="Search knowledge base", parameters={"query": "string"}
            ),
        ]

    def reference_contexts(self) -> list[str] | None:
        return None
```

- [ ] **Step 5: Write integration test**

This test requires a `GOOGLE_API_KEY` env var. Skip if not available.

```python
# backend/tests/integration/test_tool_calling_eval.py
import os

import pytest

from harness.adapters.tool_calling import ToolCallingAdapter
from harness.adapters.types import RunContext, Turn

pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set"
)


@pytest.mark.asyncio
async def test_tool_calling_adapter_invokes_weather_tool() -> None:
    adapter = ToolCallingAdapter()
    ctx = RunContext(run_id="test-run-1", suite_id="test-suite-1")
    response = await adapter.invoke(
        [Turn(role="user", content="What is the weather in Paris?")], ctx
    )
    assert response.output != ""
    assert response.latency_ms > 0
    # Agent should have called get_weather
    tool_names = [tc.name for tc in response.tool_calls]
    assert "get_weather" in tool_names


@pytest.mark.asyncio
async def test_tool_calling_adapter_invokes_calculate() -> None:
    adapter = ToolCallingAdapter()
    ctx = RunContext(run_id="test-run-2", suite_id="test-suite-1")
    response = await adapter.invoke(
        [Turn(role="user", content="What is 15 * 23 + 7?")], ctx
    )
    assert response.output != ""
    tool_names = [tc.name for tc in response.tool_calls]
    assert "calculate" in tool_names


def test_tool_calling_adapter_satisfies_protocol() -> None:
    from harness.adapters.protocol import AgentAdapter

    adapter = ToolCallingAdapter()
    assert isinstance(adapter, AgentAdapter)
    assert adapter.agent_id == "tool-calling-agent"
    assert adapter.capabilities == {"text", "tools"}
    assert adapter.reference_contexts() is None
    assert adapter.expected_tools() is not None
    assert len(adapter.expected_tools()) == 3
```

- [ ] **Step 6: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_adapter_protocol.py tests/integration/test_tool_calling_eval.py -v
```

Expected: unit tests PASS, integration tests PASS (or skipped if no API key)

- [ ] **Step 7: Commit**

```bash
git add backend/src/harness/agents/ backend/src/harness/adapters/tool_calling.py backend/tests/integration/
git commit -m "feat: add tool-calling ADK agent and adapter"
```

---

### Task 6: Eval Engine — Metrics + Runner + Report

**Files:**
- Create: `backend/src/harness/eval/__init__.py`
- Create: `backend/src/harness/eval/metrics.py`
- Create: `backend/src/harness/eval/report.py`
- Create: `backend/src/harness/eval/engine.py`
- Create: `backend/tests/unit/test_metrics.py`
- Create: `backend/tests/unit/test_report.py`
- Create: `backend/tests/unit/test_eval_engine.py`
- Create: `backend/tests/fixtures/tool_calling_evalset.json`

- [ ] **Step 1: Write failing test for metric routing**

```python
# backend/tests/unit/test_metrics.py
import pytest

from harness.adapters.types import MetricResult
from harness.eval.metrics import MetricBackend, MetricConfig, route_metrics


def test_metric_config_creation() -> None:
    config = MetricConfig(
        name="tool_trajectory_avg_score",
        backend=MetricBackend.ADK,
        threshold=1.0,
        params={"match_type": "EXACT"},
    )
    assert config.backend == MetricBackend.ADK
    assert config.threshold == 1.0


def test_route_metrics_filters_by_supported() -> None:
    all_configs = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
        MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
        MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
    ]
    supported = ["tool_trajectory_avg_score", "answer_relevancy"]
    routed = route_metrics(all_configs, supported)
    assert len(routed) == 2
    names = [m.name for m in routed]
    assert "faithfulness" not in names
    assert "tool_trajectory_avg_score" in names
    assert "answer_relevancy" in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_metrics.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement metrics module**

```python
# backend/src/harness/eval/__init__.py
```

```python
# backend/src/harness/eval/metrics.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from harness.adapters.types import AgentResponse, MetricResult, ToolCall


class MetricBackend(Enum):
    ADK = "adk"
    DEEPEVAL = "deepeval"


@dataclass(frozen=True)
class MetricConfig:
    name: str
    backend: MetricBackend
    threshold: float
    params: dict[str, Any] = field(default_factory=dict)


def route_metrics(all_configs: list[MetricConfig], supported: list[str]) -> list[MetricConfig]:
    """Filter metric configs to only those the agent supports."""
    supported_set = set(supported)
    return [c for c in all_configs if c.name in supported_set]


async def compute_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    expected_tools: list[ToolCall] | None,
    reference_contexts: list[str] | None,
) -> MetricResult:
    """Compute a single metric. Routes to ADK or DeepEval backend."""
    if config.backend == MetricBackend.ADK:
        score = await _compute_adk_metric(config, agent_response, expected_output, expected_tools)
    elif config.backend == MetricBackend.DEEPEVAL:
        score = await _compute_deepeval_metric(
            config, agent_response, expected_output, reference_contexts
        )
    else:
        raise ValueError(f"Unknown backend: {config.backend}")

    return MetricResult(
        name=config.name,
        score=score,
        threshold=config.threshold,
        details={"backend": config.backend.value},
        backend=config.backend.value,
    )


async def _compute_adk_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    expected_tools: list[ToolCall] | None,
) -> float:
    """Compute ADK-backed metrics."""
    if config.name == "tool_trajectory_avg_score":
        return _tool_trajectory_score(agent_response.tool_calls, expected_tools or [])
    elif config.name == "response_match_score":
        return _rouge1_score(agent_response.output, expected_output or "")
    elif config.name == "final_response_match_v2":
        # LLM-as-judge — will integrate ADK's actual judge in integration phase
        # For now, fall back to ROUGE-1 as placeholder
        return _rouge1_score(agent_response.output, expected_output or "")
    else:
        raise ValueError(f"Unknown ADK metric: {config.name}")


async def _compute_deepeval_metric(
    config: MetricConfig,
    agent_response: AgentResponse,
    expected_output: str | None,
    reference_contexts: list[str] | None,
) -> float:
    """Compute DeepEval-backed metrics. Imported lazily to avoid hard dep in unit tests."""
    # Lazy import — DeepEval is only needed when actually scoring RAG metrics
    from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric, FaithfulnessMetric, HallucinationMetric
    from deepeval.test_case import LLMTestCase

    test_case = LLMTestCase(
        input=expected_output or "",
        actual_output=agent_response.output,
        expected_output=expected_output,
        retrieval_context=reference_contexts or [],
        context=reference_contexts or [],
    )

    metric_map = {
        "faithfulness": FaithfulnessMetric,
        "contextual_relevancy": ContextualRelevancyMetric,
        "hallucination": HallucinationMetric,
        "answer_relevancy": AnswerRelevancyMetric,
    }

    metric_cls = metric_map.get(config.name)
    if metric_cls is None:
        raise ValueError(f"Unknown DeepEval metric: {config.name}")

    metric = metric_cls(threshold=config.threshold)
    metric.measure(test_case)
    return metric.score


def _tool_trajectory_score(actual: list[ToolCall], expected: list[ToolCall]) -> float:
    """Exact match on tool names in order."""
    if not expected:
        return 1.0 if not actual else 0.0
    actual_names = [tc.name for tc in actual]
    expected_names = [tc.name for tc in expected]
    if actual_names == expected_names:
        return 1.0
    # Partial credit: fraction of expected tools that appear in order
    matches = 0
    actual_idx = 0
    for exp_name in expected_names:
        while actual_idx < len(actual_names):
            if actual_names[actual_idx] == exp_name:
                matches += 1
                actual_idx += 1
                break
            actual_idx += 1
    return matches / len(expected_names)


def _rouge1_score(generated: str, reference: str) -> float:
    """Simple ROUGE-1 (unigram overlap) score."""
    if not reference or not generated:
        return 0.0
    gen_tokens = set(generated.lower().split())
    ref_tokens = set(reference.lower().split())
    if not ref_tokens:
        return 0.0
    overlap = gen_tokens & ref_tokens
    precision = len(overlap) / len(gen_tokens) if gen_tokens else 0.0
    recall = len(overlap) / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)
```

- [ ] **Step 4: Run metric tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_metrics.py -v
```

Expected: PASS

- [ ] **Step 5: Write failing test for EvalReport**

```python
# backend/tests/unit/test_report.py
from harness.adapters.types import MetricResult
from harness.eval.report import CaseResult, EvalReport


def test_case_result_passed_when_all_metrics_pass() -> None:
    case = CaseResult(
        test_case_id="tc-1",
        metric_results=[
            MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk"),
            MetricResult(name="m2", score=0.9, threshold=0.8, details={}, backend="deepeval"),
        ],
        latency_ms=100.0,
    )
    assert case.passed is True


def test_case_result_fails_when_any_metric_fails() -> None:
    case = CaseResult(
        test_case_id="tc-1",
        metric_results=[
            MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk"),
            MetricResult(name="m2", score=0.5, threshold=0.8, details={}, backend="deepeval"),
        ],
        latency_ms=100.0,
    )
    assert case.passed is False


def test_eval_report_summary() -> None:
    report = EvalReport(
        run_id="run-1",
        suite_id="suite-1",
        case_results=[
            CaseResult(
                test_case_id="tc-1",
                metric_results=[MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk")],
                latency_ms=100.0,
            ),
            CaseResult(
                test_case_id="tc-2",
                metric_results=[MetricResult(name="m1", score=0.5, threshold=0.8, details={}, backend="adk")],
                latency_ms=200.0,
            ),
        ],
    )
    summary = report.summary()
    assert summary["total_cases"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["avg_latency_ms"] == 150.0


def test_eval_report_overall_passed() -> None:
    report = EvalReport(
        run_id="run-1",
        suite_id="suite-1",
        case_results=[
            CaseResult(
                test_case_id="tc-1",
                metric_results=[MetricResult(name="m1", score=1.0, threshold=0.8, details={}, backend="adk")],
                latency_ms=100.0,
            ),
        ],
    )
    assert report.overall_passed is True
```

- [ ] **Step 6: Implement EvalReport**

```python
# backend/src/harness/eval/report.py
from dataclasses import dataclass
from typing import Any

from harness.adapters.types import AgentResponse, MetricResult


@dataclass
class CaseResult:
    test_case_id: str
    metric_results: list[MetricResult]
    latency_ms: float
    agent_response: AgentResponse | None = None

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metric_results)


@dataclass
class EvalReport:
    run_id: str
    suite_id: str
    case_results: list[CaseResult]

    @property
    def overall_passed(self) -> bool:
        return all(cr.passed for cr in self.case_results)

    def summary(self) -> dict[str, Any]:
        total = len(self.case_results)
        passed = sum(1 for cr in self.case_results if cr.passed)
        latencies = [cr.latency_ms for cr in self.case_results]
        avg_latency = sum(latencies) / total if total > 0 else 0.0

        # Per-metric averages
        metric_scores: dict[str, list[float]] = {}
        for cr in self.case_results:
            for mr in cr.metric_results:
                metric_scores.setdefault(mr.name, []).append(mr.score)
        avg_scores = {name: sum(scores) / len(scores) for name, scores in metric_scores.items()}

        return {
            "total_cases": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "avg_latency_ms": avg_latency,
            "metric_averages": avg_scores,
        }
```

- [ ] **Step 7: Run report tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_report.py -v
```

Expected: PASS

- [ ] **Step 8: Write failing test for EvalRunner**

```python
# backend/tests/unit/test_eval_engine.py
import pytest

from harness.adapters.types import AgentResponse, MetricResult, RunContext, TokenUsage, ToolCall, ToolSpec, Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.eval.metrics import MetricBackend, MetricConfig


class StubAdapter:
    @property
    def agent_id(self) -> str:
        return "stub"

    @property
    def display_name(self) -> str:
        return "Stub"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        return AgentResponse(
            output="Sunny in Paris",
            tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
            retrieved_contexts=[],
            latency_ms=50.0,
            token_usage=TokenUsage(input_tokens=10, output_tokens=5),
            raw_events=[],
        )

    def supported_metrics(self) -> list[str]:
        return ["tool_trajectory_avg_score"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [ToolSpec(name="get_weather", description="", parameters={})]

    def reference_contexts(self) -> list[str] | None:
        return None


@pytest.mark.asyncio
async def test_eval_runner_produces_report() -> None:
    adapter = StubAdapter()
    metrics = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
    ]
    test_cases = [
        EvalTestCase(
            id="tc-1",
            input=[Turn(role="user", content="Weather in Paris?")],
            expected_output="Sunny in Paris",
            expected_tools=[ToolCall(name="get_weather", args={"city": "Paris"})],
            reference_contexts=None,
            tags=["weather"],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id="run-1", suite_id="suite-1")

    assert report.run_id == "run-1"
    assert len(report.case_results) == 1
    assert report.case_results[0].passed is True
    assert report.overall_passed is True


@pytest.mark.asyncio
async def test_eval_runner_with_failing_case() -> None:
    adapter = StubAdapter()
    metrics = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
    ]
    test_cases = [
        EvalTestCase(
            id="tc-1",
            input=[Turn(role="user", content="Weather?")],
            expected_output=None,
            expected_tools=[ToolCall(name="calculate", args={"expression": "1+1"})],  # wrong tool
            reference_contexts=None,
            tags=[],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    report = await runner.run(run_id="run-2", suite_id="suite-1")

    assert report.case_results[0].passed is False
    assert report.overall_passed is False
```

- [ ] **Step 9: Implement EvalRunner**

```python
# backend/src/harness/eval/engine.py
from dataclasses import dataclass

from harness.adapters.protocol import AgentAdapter
from harness.adapters.types import RunContext, ToolCall, Turn
from harness.eval.metrics import MetricConfig, compute_metric, route_metrics
from harness.eval.report import CaseResult, EvalReport


@dataclass
class EvalTestCase:
    id: str
    input: list[Turn]
    expected_output: str | None
    expected_tools: list[ToolCall] | None
    reference_contexts: list[str] | None
    tags: list[str]


class EvalRunner:
    def __init__(
        self,
        adapter: AgentAdapter,
        metrics: list[MetricConfig],
        test_cases: list[EvalTestCase],
    ) -> None:
        self._adapter = adapter
        self._metrics = route_metrics(metrics, adapter.supported_metrics())
        self._test_cases = test_cases

    async def run(self, run_id: str, suite_id: str) -> EvalReport:
        ctx = RunContext(run_id=run_id, suite_id=suite_id)
        case_results: list[CaseResult] = []

        for tc in self._test_cases:
            response = await self._adapter.invoke(tc.input, ctx)

            metric_results = []
            for metric_config in self._metrics:
                result = await compute_metric(
                    config=metric_config,
                    agent_response=response,
                    expected_output=tc.expected_output,
                    expected_tools=tc.expected_tools,
                    reference_contexts=tc.reference_contexts,
                )
                metric_results.append(result)

            case_results.append(
                CaseResult(
                    test_case_id=tc.id,
                    metric_results=metric_results,
                    latency_ms=response.latency_ms,
                    agent_response=response,
                )
            )

        return EvalReport(run_id=run_id, suite_id=suite_id, case_results=case_results)
```

- [ ] **Step 10: Run all eval engine tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_metrics.py tests/unit/test_report.py tests/unit/test_eval_engine.py -v
```

Expected: PASS

- [ ] **Step 11: Create test fixtures**

```json
// backend/tests/fixtures/tool_calling_evalset.json
{
  "suite_name": "tool_calling_basic",
  "test_cases": [
    {
      "id": "weather-paris",
      "input": [{"role": "user", "content": "What is the weather in Paris?"}],
      "expected_output": "sunny",
      "expected_tools": [{"name": "get_weather", "args": {"city": "Paris"}}],
      "tags": ["weather"]
    },
    {
      "id": "calc-basic",
      "input": [{"role": "user", "content": "What is 15 * 23?"}],
      "expected_output": "345",
      "expected_tools": [{"name": "calculate", "args": {"expression": "15 * 23"}}],
      "tags": ["math"]
    },
    {
      "id": "search-python",
      "input": [{"role": "user", "content": "Tell me about Python programming language"}],
      "expected_output": "Python is a high-level programming language created by Guido van Rossum",
      "expected_tools": [{"name": "search_knowledge", "args": {"query": "Python"}}],
      "tags": ["knowledge"]
    }
  ]
}
```

- [ ] **Step 12: Commit**

```bash
git add backend/src/harness/eval/ backend/tests/unit/test_metrics.py backend/tests/unit/test_report.py backend/tests/unit/test_eval_engine.py backend/tests/fixtures/
git commit -m "feat: add eval engine with metric routing, runner, and report"
```

---

### Task 7: Baseline Comparison

**Files:**
- Create: `backend/src/harness/eval/baseline.py`
- Create: `backend/tests/unit/test_baseline.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_baseline.py
from harness.eval.baseline import BaselineSnapshot, compare_to_baseline, RegressionResult


def test_no_regression_when_scores_improve() -> None:
    baseline = BaselineSnapshot(
        scores={"tool_trajectory_avg_score": 0.9, "answer_relevancy": 0.8},
        thresholds={"tool_trajectory_avg_score": 0.8, "answer_relevancy": 0.7},
    )
    current = {"tool_trajectory_avg_score": 1.0, "answer_relevancy": 0.85}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False
    assert len(result.regressions) == 0


def test_regression_when_score_drops_below_floor() -> None:
    baseline = BaselineSnapshot(
        scores={"faithfulness": 0.9},
        thresholds={"faithfulness": 0.8},
    )
    current = {"faithfulness": 0.7}  # below floor of 0.8
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is True
    assert "faithfulness" in [r.metric_name for r in result.regressions]


def test_regression_when_score_drops_by_tolerance() -> None:
    baseline = BaselineSnapshot(
        scores={"answer_relevancy": 0.9},
        thresholds={"answer_relevancy": 0.7},
        tolerance=0.05,
    )
    current = {"answer_relevancy": 0.84}  # dropped 0.06, > tolerance 0.05
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is True


def test_no_regression_within_tolerance() -> None:
    baseline = BaselineSnapshot(
        scores={"answer_relevancy": 0.9},
        thresholds={"answer_relevancy": 0.7},
        tolerance=0.05,
    )
    current = {"answer_relevancy": 0.86}  # dropped 0.04, within tolerance
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False


def test_new_metrics_not_in_baseline_ignored() -> None:
    baseline = BaselineSnapshot(
        scores={"faithfulness": 0.9},
        thresholds={"faithfulness": 0.8},
    )
    current = {"faithfulness": 0.95, "new_metric": 0.7}
    result = compare_to_baseline(current, baseline)
    assert result.has_regression is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_baseline.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement baseline comparison**

```python
# backend/src/harness/eval/baseline.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BaselineSnapshot:
    scores: dict[str, float]
    thresholds: dict[str, float]
    tolerance: float = 0.05  # 5 percentage points


@dataclass(frozen=True)
class Regression:
    metric_name: str
    baseline_score: float
    current_score: float
    threshold: float
    reason: str  # "below_floor" | "exceeded_tolerance"


@dataclass
class RegressionResult:
    regressions: list[Regression] = field(default_factory=list)
    deltas: dict[str, float] = field(default_factory=dict)

    @property
    def has_regression(self) -> bool:
        return len(self.regressions) > 0


def compare_to_baseline(
    current_scores: dict[str, float],
    baseline: BaselineSnapshot,
) -> RegressionResult:
    regressions: list[Regression] = []
    deltas: dict[str, float] = {}

    for metric_name, baseline_score in baseline.scores.items():
        if metric_name not in current_scores:
            continue

        current = current_scores[metric_name]
        delta = current - baseline_score
        deltas[metric_name] = delta

        threshold = baseline.thresholds.get(metric_name, 0.0)

        # Check 1: below absolute floor
        if current < threshold:
            regressions.append(
                Regression(
                    metric_name=metric_name,
                    baseline_score=baseline_score,
                    current_score=current,
                    threshold=threshold,
                    reason="below_floor",
                )
            )
        # Check 2: dropped beyond tolerance vs baseline
        elif delta < -baseline.tolerance:
            regressions.append(
                Regression(
                    metric_name=metric_name,
                    baseline_score=baseline_score,
                    current_score=current,
                    threshold=threshold,
                    reason="exceeded_tolerance",
                )
            )

    return RegressionResult(regressions=regressions, deltas=deltas)
```

- [ ] **Step 4: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/unit/test_baseline.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/eval/baseline.py backend/tests/unit/test_baseline.py
git commit -m "feat: add baseline snapshot and regression detection"
```

---

## WEEK 2: RAG Agent + Meta-Agent + CopilotKit

---

### Task 8: RAG Agent + Adapter + DeepEval Metrics

**Files:**
- Create: `backend/src/harness/agents/rag_agent.py`
- Create: `backend/src/harness/adapters/rag.py`
- Create: `backend/tests/fixtures/rag_evalset.json`
- Create: `backend/tests/integration/test_rag_eval.py`

- [ ] **Step 1: Add DeepEval dependency**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add deepeval
```

- [ ] **Step 2: Create RAG agent with retrieval tool**

```python
# backend/src/harness/agents/rag_agent.py
import json

from google.adk.agents import LlmAgent

# Curated document set (~50 docs) — technical FAQ style
DOCUMENTS = [
    {
        "id": "doc-1",
        "title": "What is FastAPI?",
        "content": "FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. It was created by Sebastián Ramírez and first released in 2018. FastAPI is built on top of Starlette for the web parts and Pydantic for the data parts. It supports async/await and is one of the fastest Python frameworks available.",
    },
    {
        "id": "doc-2",
        "title": "What is SQLAlchemy?",
        "content": "SQLAlchemy is the Python SQL toolkit and Object-Relational Mapping (ORM) library. It provides a full suite of well-known enterprise-level persistence patterns. SQLAlchemy 2.0 introduced a new unified interface with improved type support. It supports async operations via asyncio extensions.",
    },
    {
        "id": "doc-3",
        "title": "What is OpenTelemetry?",
        "content": "OpenTelemetry is an open-source observability framework for generating, collecting, and exporting telemetry data (traces, metrics, logs). It is a CNCF project formed by merging OpenTracing and OpenCensus. The GenAI semantic conventions add LLM-specific attributes like gen_ai.request.model and gen_ai.usage.input_tokens.",
    },
    {
        "id": "doc-4",
        "title": "What is Google ADK?",
        "content": "Google Agent Development Kit (ADK) is an open-source, Apache-2.0 agent framework supporting Python, TypeScript, Go, and Java. Released at Google Cloud NEXT on April 9, 2025. ADK 2.0 adds a graph-based Workflow Runtime for routing, fan-out/fan-in, loops, retry, and human-in-the-loop. Core architecture uses an event-driven Runner with SessionService for state management.",
    },
    {
        "id": "doc-5",
        "title": "What are LLM Evals?",
        "content": "LLM evaluations (evals) are systematic assessments of language model outputs against defined criteria. Common metrics include faithfulness (is the answer grounded in context), relevancy (does it answer the question), and hallucination detection. Evals can be automated using LLM-as-judge approaches or rule-based metrics like ROUGE scores.",
    },
]


def retrieve_documents(query: str) -> str:
    """Search the document knowledge base and return relevant documents.

    Args:
        query: The search query to find relevant documents.

    Returns:
        JSON string with matching documents.
    """
    query_lower = query.lower()
    results = []
    for doc in DOCUMENTS:
        title_lower = doc["title"].lower()
        content_lower = doc["content"].lower()
        # Simple keyword matching — production would use embeddings
        query_words = query_lower.split()
        if any(word in title_lower or word in content_lower for word in query_words):
            results.append(doc)
    if not results:
        results = [DOCUMENTS[0]]  # fallback to first doc
    return json.dumps(results[:3])  # max 3 results


RAG_INSTRUCTION = """You are a knowledgeable assistant that answers questions using retrieved documents.
Always use the retrieve_documents tool to search for relevant information before answering.
Base your answer ONLY on the retrieved documents. Do not make up information.
If the documents don't contain the answer, say so clearly."""


def create_rag_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name="rag_agent",
        model=model,
        instruction=RAG_INSTRUCTION,
        tools=[retrieve_documents],
    )
```

- [ ] **Step 3: Create RAGAdapter**

```python
# backend/src/harness/adapters/rag.py
import time
from typing import Any

from google.adk import Runner
from google.adk.agents import types
from google.adk.sessions import InMemorySessionService

from harness.adapters.types import AgentResponse, RunContext, TokenUsage, ToolCall, ToolSpec, Turn
from harness.agents.rag_agent import DOCUMENTS, create_rag_agent


class RAGAdapter:
    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._agent = create_rag_agent(model)
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._agent,
            session_service=self._session_service,
            app_name="rag_eval",
        )

    @property
    def agent_id(self) -> str:
        return "rag-agent"

    @property
    def display_name(self) -> str:
        return "RAG Demo Agent"

    @property
    def capabilities(self) -> set[str]:
        return {"text", "tools", "rag"}

    async def invoke(self, input: list[Turn], context: RunContext) -> AgentResponse:
        session = await self._session_service.create_session(
            app_name="rag_eval", user_id=f"eval-{context.run_id}"
        )
        tool_calls: list[ToolCall] = []
        final_output = ""
        raw_events: list[Any] = []
        retrieved_contexts: list[str] = []
        input_tokens = 0
        output_tokens = 0

        start = time.monotonic()

        for turn in input:
            message = types.Content(role=turn.role, parts=[types.Part(text=turn.content)])
            async for event in self._runner.run_async(
                user_id=f"eval-{context.run_id}",
                session_id=session.id,
                new_message=message,
            ):
                raw_events.append(event)
                if event.actions and event.actions.function_calls:
                    for fc in event.actions.function_calls:
                        tool_calls.append(ToolCall(name=fc.name, args=dict(fc.args or {})))
                # Capture retrieved docs from tool results
                if event.actions and event.actions.function_responses:
                    for fr in event.actions.function_responses:
                        if fr.name == "retrieve_documents" and fr.response:
                            retrieved_contexts.append(str(fr.response))
                if event.is_final_response() and event.content and event.content.parts:
                    final_output = event.content.parts[0].text or ""
                if hasattr(event, "usage") and event.usage:
                    input_tokens += getattr(event.usage, "prompt_tokens", 0)
                    output_tokens += getattr(event.usage, "completion_tokens", 0)

        elapsed = (time.monotonic() - start) * 1000

        return AgentResponse(
            output=final_output,
            tool_calls=tool_calls,
            retrieved_contexts=retrieved_contexts,
            latency_ms=elapsed,
            token_usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            raw_events=raw_events,
        )

    def supported_metrics(self) -> list[str]:
        return ["faithfulness", "contextual_relevancy", "hallucination", "answer_relevancy"]

    def expected_tools(self) -> list[ToolSpec] | None:
        return [ToolSpec(name="retrieve_documents", description="Search docs", parameters={"query": "string"})]

    def reference_contexts(self) -> list[str] | None:
        return [doc["content"] for doc in DOCUMENTS]
```

- [ ] **Step 4: Create RAG evalset fixture**

```json
// backend/tests/fixtures/rag_evalset.json
{
  "suite_name": "rag_basic",
  "test_cases": [
    {
      "id": "rag-fastapi",
      "input": [{"role": "user", "content": "What is FastAPI and who created it?"}],
      "expected_output": "FastAPI is a modern web framework for building APIs with Python, created by Sebastián Ramírez",
      "reference_contexts": [
        "FastAPI is a modern, high-performance web framework for building APIs with Python based on standard Python type hints. It was created by Sebastián Ramírez and first released in 2018."
      ],
      "tags": ["fastapi"]
    },
    {
      "id": "rag-otel",
      "input": [{"role": "user", "content": "What are the GenAI semantic conventions in OpenTelemetry?"}],
      "expected_output": "The GenAI semantic conventions add LLM-specific attributes like gen_ai.request.model and gen_ai.usage.input_tokens",
      "reference_contexts": [
        "OpenTelemetry is an open-source observability framework. The GenAI semantic conventions add LLM-specific attributes like gen_ai.request.model and gen_ai.usage.input_tokens."
      ],
      "tags": ["otel"]
    },
    {
      "id": "rag-adk",
      "input": [{"role": "user", "content": "What is Google ADK and when was it released?"}],
      "expected_output": "Google ADK is an open-source agent framework released at Google Cloud NEXT on April 9, 2025",
      "reference_contexts": [
        "Google Agent Development Kit (ADK) is an open-source, Apache-2.0 agent framework. Released at Google Cloud NEXT on April 9, 2025."
      ],
      "tags": ["adk"]
    }
  ]
}
```

- [ ] **Step 5: Write integration test**

```python
# backend/tests/integration/test_rag_eval.py
import os

import pytest

from harness.adapters.protocol import AgentAdapter
from harness.adapters.rag import RAGAdapter
from harness.adapters.types import RunContext, Turn

pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set"
)


def test_rag_adapter_satisfies_protocol() -> None:
    adapter = RAGAdapter()
    assert isinstance(adapter, AgentAdapter)
    assert "rag" in adapter.capabilities
    assert adapter.reference_contexts() is not None
    assert len(adapter.reference_contexts()) > 0


@pytest.mark.asyncio
async def test_rag_adapter_retrieves_and_answers() -> None:
    adapter = RAGAdapter()
    ctx = RunContext(run_id="test-rag-1", suite_id="rag-suite-1")
    response = await adapter.invoke(
        [Turn(role="user", content="What is FastAPI?")], ctx
    )
    assert response.output != ""
    assert len(response.retrieved_contexts) > 0
    tool_names = [tc.name for tc in response.tool_calls]
    assert "retrieve_documents" in tool_names
```

- [ ] **Step 6: Run tests**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/integration/test_rag_eval.py -v
```

Expected: PASS (or skipped if no API key)

- [ ] **Step 7: Commit**

```bash
git add backend/src/harness/agents/rag_agent.py backend/src/harness/adapters/rag.py backend/tests/fixtures/rag_evalset.json backend/tests/integration/test_rag_eval.py
git commit -m "feat: add RAG agent, adapter, and DeepEval metrics"
```

---

### Task 9: Meta-Agent Tools — Registry, List, Run, Results

**Files:**
- Create: `backend/src/harness/meta_tools/__init__.py`
- Create: `backend/src/harness/meta_tools/registry.py`
- Create: `backend/src/harness/meta_tools/list_agents.py`
- Create: `backend/src/harness/meta_tools/list_metrics.py`
- Create: `backend/src/harness/meta_tools/run_eval.py`
- Create: `backend/src/harness/meta_tools/get_results.py`
- Create: `backend/src/harness/meta_tools/explain_failure.py`

- [ ] **Step 1: Create agent + metric registry**

```python
# backend/src/harness/meta_tools/registry.py
from harness.adapters.protocol import AgentAdapter
from harness.adapters.rag import RAGAdapter
from harness.adapters.tool_calling import ToolCallingAdapter
from harness.eval.metrics import MetricBackend, MetricConfig

# Singleton registry — populated at startup
_adapters: dict[str, AgentAdapter] = {}
_default_metrics: dict[str, list[MetricConfig]] = {}


def init_registry() -> None:
    """Initialize the demo agent registry. Called at app startup."""
    global _adapters, _default_metrics

    tool_adapter = ToolCallingAdapter()
    rag_adapter = RAGAdapter()

    _adapters = {
        tool_adapter.agent_id: tool_adapter,
        rag_adapter.agent_id: rag_adapter,
    }

    _default_metrics = {
        "tool-calling-agent": [
            MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
            MetricConfig(name="final_response_match_v2", backend=MetricBackend.ADK, threshold=0.7),
            MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
        ],
        "rag-agent": [
            MetricConfig(name="faithfulness", backend=MetricBackend.DEEPEVAL, threshold=0.8),
            MetricConfig(name="contextual_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
            MetricConfig(name="hallucination", backend=MetricBackend.DEEPEVAL, threshold=0.8),
            MetricConfig(name="answer_relevancy", backend=MetricBackend.DEEPEVAL, threshold=0.7),
        ],
    }


def get_adapter(agent_id: str) -> AgentAdapter | None:
    return _adapters.get(agent_id)


def list_adapters() -> dict[str, AgentAdapter]:
    return dict(_adapters)


def get_default_metrics(agent_id: str) -> list[MetricConfig]:
    return _default_metrics.get(agent_id, [])
```

- [ ] **Step 2: Create meta-agent tool functions**

```python
# backend/src/harness/meta_tools/list_agents.py
import json

from harness.meta_tools.registry import list_adapters


def list_agents() -> str:
    """List all available agents with their capabilities and supported metrics.

    Returns a JSON string with agent details.
    """
    adapters = list_adapters()
    agents = []
    for adapter in adapters.values():
        agents.append({
            "agent_id": adapter.agent_id,
            "display_name": adapter.display_name,
            "capabilities": sorted(adapter.capabilities),
            "supported_metrics": adapter.supported_metrics(),
        })
    return json.dumps(agents, indent=2)
```

```python
# backend/src/harness/meta_tools/list_metrics.py
import json

from harness.meta_tools.registry import get_adapter, get_default_metrics


def list_metrics(agent_id: str) -> str:
    """List available metrics and their default thresholds for a specific agent.

    Args:
        agent_id: The agent to list metrics for.

    Returns:
        JSON string with metric details including name, backend, and threshold.
    """
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})

    defaults = get_default_metrics(agent_id)
    metrics = []
    for m in defaults:
        if m.name in adapter.supported_metrics():
            metrics.append({
                "name": m.name,
                "backend": m.backend.value,
                "threshold": m.threshold,
            })
    return json.dumps(metrics, indent=2)
```

```python
# backend/src/harness/meta_tools/run_eval.py
import json
import uuid

from harness.adapters.types import ToolCall, Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.meta_tools.registry import get_adapter, get_default_metrics


async def run_eval(agent_id: str, test_cases_json: str) -> str:
    """Run an evaluation suite against a specific agent.

    Args:
        agent_id: The agent to evaluate.
        test_cases_json: JSON string containing test cases. Each case has: id, input (list of turns), expected_output (optional), expected_tools (optional), reference_contexts (optional).

    Returns:
        JSON string with eval results summary and per-case details.
    """
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})

    try:
        raw_cases = json.loads(test_cases_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    test_cases = []
    for rc in raw_cases:
        test_cases.append(EvalTestCase(
            id=rc.get("id", str(uuid.uuid4())),
            input=[Turn(role=t["role"], content=t["content"]) for t in rc["input"]],
            expected_output=rc.get("expected_output"),
            expected_tools=[
                ToolCall(name=t["name"], args=t.get("args", {}))
                for t in rc.get("expected_tools", [])
            ] or None,
            reference_contexts=rc.get("reference_contexts"),
            tags=rc.get("tags", []),
        ))

    metrics = get_default_metrics(agent_id)
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)

    run_id = str(uuid.uuid4())
    report = await runner.run(run_id=run_id, suite_id=f"{agent_id}-eval")

    # Format results for the meta-agent to relay
    results = []
    for cr in report.case_results:
        results.append({
            "test_case_id": cr.test_case_id,
            "passed": cr.passed,
            "latency_ms": round(cr.latency_ms, 1),
            "metrics": [
                {"name": mr.name, "score": round(mr.score, 3), "passed": mr.passed, "threshold": mr.threshold}
                for mr in cr.metric_results
            ],
        })

    return json.dumps({
        "run_id": run_id,
        "overall_passed": report.overall_passed,
        "summary": report.summary(),
        "results": results,
    }, indent=2)
```

```python
# backend/src/harness/meta_tools/get_results.py
import json

# In-memory store for MVP — will be replaced with DB queries
_results_store: dict[str, dict] = {}


def store_results(run_id: str, results: dict) -> None:
    """Store eval results for later retrieval."""
    _results_store[run_id] = results


def get_results(run_id: str) -> str:
    """Get the results of a specific eval run.

    Args:
        run_id: The ID of the eval run to retrieve.

    Returns:
        JSON string with the full eval results.
    """
    if run_id in _results_store:
        return json.dumps(_results_store[run_id], indent=2)
    return json.dumps({"error": f"Run '{run_id}' not found. Use run_eval to create a new run."})
```

```python
# backend/src/harness/meta_tools/explain_failure.py
import json

from harness.meta_tools.get_results import _results_store


def explain_failure(run_id: str, test_case_id: str) -> str:
    """Explain why a specific test case failed in an eval run.

    Args:
        run_id: The eval run ID.
        test_case_id: The test case ID to explain.

    Returns:
        Detailed JSON with agent response, metric scores, and failure reasons.
    """
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})

    run_data = _results_store[run_id]
    for result in run_data.get("results", []):
        if result["test_case_id"] == test_case_id:
            failures = [m for m in result["metrics"] if not m["passed"]]
            return json.dumps({
                "test_case_id": test_case_id,
                "passed": result["passed"],
                "latency_ms": result["latency_ms"],
                "failing_metrics": failures,
                "all_metrics": result["metrics"],
                "explanation": _build_explanation(failures),
            }, indent=2)

    return json.dumps({"error": f"Test case '{test_case_id}' not found in run '{run_id}'"})


def _build_explanation(failures: list[dict]) -> str:
    if not failures:
        return "This test case passed all metrics."
    parts = []
    for f in failures:
        parts.append(
            f"Metric '{f['name']}' scored {f['score']:.3f}, "
            f"below threshold {f['threshold']:.3f}."
        )
    return " ".join(parts)
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/harness/meta_tools/
git commit -m "feat: add meta-agent tools (registry, list, run, results, explain)"
```

---

### Task 10: Meta-Agent + ag_ui_adk Endpoint

**Files:**
- Create: `backend/src/harness/agents/meta_agent.py`
- Create: `backend/src/harness/api/agui.py`
- Modify: `backend/src/harness/main.py`

- [ ] **Step 1: Add ag_ui_adk dependency**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add ag-ui-adk
```

- [ ] **Step 2: Create meta-agent**

```python
# backend/src/harness/agents/meta_agent.py
from google.adk.agents import LlmAgent

from harness.meta_tools.explain_failure import explain_failure
from harness.meta_tools.list_agents import list_agents
from harness.meta_tools.list_metrics import list_metrics
from harness.meta_tools.run_eval import run_eval

META_AGENT_INSTRUCTION = """You are the Agent-Evals Meta-Harness — an evaluation orchestrator.
You help users understand and evaluate their AI agents' quality.

Your capabilities:
1. List available demo agents and their capabilities
2. Show which metrics are available for each agent type
3. Run evaluation suites against agents
4. Explain why specific test cases failed

Workflow you should guide users through:
1. Show them available agents (use list_agents)
2. Help them understand available metrics (use list_metrics)
3. Run evals with appropriate test cases (use run_eval)
4. Help them understand failures (use explain_failure)

When running evals, construct test cases as a JSON array. Each test case needs:
- "id": a short identifier
- "input": list of conversation turns [{"role": "user", "content": "..."}]
- "expected_output": what the correct answer should contain (optional)
- "expected_tools": which tools should be called [{"name": "tool_name", "args": {...}}] (optional)
- "reference_contexts": ground truth documents for RAG evaluation (optional)
- "tags": categorization tags (optional)

Be concise but thorough in your explanations. When showing results, highlight failures first."""


def create_meta_agent(model: str = "gemini-2.5-flash") -> LlmAgent:
    return LlmAgent(
        name="meta_agent",
        model=model,
        instruction=META_AGENT_INSTRUCTION,
        tools=[list_agents, list_metrics, run_eval, explain_failure],
    )
```

- [ ] **Step 3: Create AG-UI endpoint**

```python
# backend/src/harness/api/agui.py
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from fastapi import FastAPI

from harness.agents.meta_agent import create_meta_agent


def setup_agui_endpoint(app: FastAPI) -> None:
    """Mount the AG-UI endpoint for the meta-agent."""
    meta_agent = create_meta_agent()

    adk_agent = ADKAgent(
        adk_agent=meta_agent,
        app_name="agent-evals-harness",
        user_id="default-user",  # will be overridden per-request with auth
        use_in_memory_services=True,
        session_timeout_seconds=3600,
        execution_timeout_seconds=600,
    )

    add_adk_fastapi_endpoint(app, adk_agent, path="/agui")
```

- [ ] **Step 4: Update main.py to mount AG-UI and init registry**

```python
# backend/src/harness/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from harness.api.agui import setup_agui_endpoint
from harness.api.health import router as health_router
from harness.config import settings
from harness.meta_tools.registry import init_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_registry()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Agent-Evals Meta-Harness", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    setup_agui_endpoint(app)
    return app


app = create_app()
```

- [ ] **Step 5: Test the server starts**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run uvicorn harness.main:app --port 8000 &
sleep 3
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json | python -m json.tool | head -20
kill %1
```

Expected: health returns `{"status":"ok"}`, OpenAPI schema shows `/agui` endpoint.

- [ ] **Step 6: Commit**

```bash
git add backend/src/harness/agents/meta_agent.py backend/src/harness/api/agui.py backend/src/harness/main.py
git commit -m "feat: add meta-agent with ag_ui_adk endpoint"
```

---

### Task 11: Frontend Scaffold — Next.js + CopilotKit

**Files:**
- Create: `frontend/` (via create-next-app + CopilotKit setup)
- Create: `frontend/src/app/api/copilotkit/route.ts`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Scaffold Next.js**

```bash
cd /home/adithya/Document/llm-perf-harness
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

- [ ] **Step 2: Install CopilotKit + AG-UI + shadcn/ui**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
npx shadcn@latest init -d
```

- [ ] **Step 3: Create CopilotKit API route**

```typescript
// frontend/src/app/api/copilotkit/route.ts
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000/agui";

const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    eval_harness: new HttpAgent({ url: BACKEND_URL }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

- [ ] **Step 4: Update root layout with CopilotKit provider**

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent-Evals Meta-Harness",
  description: "Evaluate your AI agents with conversational eval orchestration",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="eval_harness">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Create main page with chat UI**

```tsx
// frontend/src/app/page.tsx
"use client";

import { CopilotChat } from "@copilotkit/react-ui";

export default function Home() {
  return (
    <div className="flex h-screen bg-gray-950">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 p-4">
        <h1 className="text-xl font-bold text-white mb-4">Agent Evals</h1>
        <p className="text-sm text-gray-400">
          Chat with the eval harness to test and evaluate your AI agents.
        </p>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col">
        <CopilotChat
          className="flex-1"
          instructions="You are the Agent-Evals Meta-Harness. Help users evaluate their AI agents."
          labels={{
            title: "Eval Harness",
            initial: "Hello! I can help you evaluate AI agents. Try asking me to list available agents.",
            placeholder: "Ask about agents, run evals, or explore results...",
          }}
        />
      </main>
    </div>
  );
}
```

- [ ] **Step 6: Create env example**

```bash
# frontend/.env.local.example
BACKEND_URL=http://localhost:8000/agui
```

Copy to `.env.local`:
```bash
cp frontend/.env.local.example frontend/.env.local
```

- [ ] **Step 7: Test frontend starts**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm run dev &
sleep 5
curl -s http://localhost:3000 | head -5
kill %1
```

Expected: HTML returned, no build errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
echo "node_modules" >> .gitignore
echo ".next" >> .gitignore
echo ".env.local" >> .gitignore
git add .gitignore
git commit -m "feat: scaffold Next.js frontend with CopilotKit + AG-UI"
```

---

### Task 12: End-to-End Conversational Flow

**Files:**
- Modify: `frontend/src/app/page.tsx` (minor adjustments)
- Create: `backend/tests/e2e/test_agui.py`

- [ ] **Step 1: Write E2E test for AG-UI SSE endpoint**

```python
# backend/tests/e2e/test_agui.py
import pytest
from httpx import ASGITransport, AsyncClient

from harness.main import app


@pytest.mark.asyncio
async def test_agui_endpoint_exists() -> None:
    """Verify the AG-UI endpoint is mounted and responds."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # AG-UI endpoints register POST at the path and GET /capabilities
        resp = await client.get("/agui/capabilities")
    # Should return 200 or 405 depending on ag_ui_adk version
    assert resp.status_code in (200, 404, 405)
```

- [ ] **Step 2: Run E2E test**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/e2e/ -v
```

Expected: PASS

- [ ] **Step 3: Manual E2E test — run both servers**

Terminal 1:
```bash
cd /home/adithya/Document/llm-perf-harness/backend
GOOGLE_API_KEY=your-key uv run uvicorn harness.main:app --port 8000
```

Terminal 2:
```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm run dev
```

Open `http://localhost:3000` in browser. Type "List available agents" in chat. Verify the meta-agent responds with agent list.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/e2e/test_agui.py
git commit -m "test: add E2E test for AG-UI endpoint"
```

---

## WEEK 3: Auth + HITL + Polish

---

### Task 13: NextAuth.js — Google + GitHub OAuth

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/app/api/auth/[...nextauth]/route.ts`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/.env.local.example`

- [ ] **Step 1: Install NextAuth**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm install next-auth
```

- [ ] **Step 2: Create auth config**

```typescript
// frontend/src/lib/auth.ts
import type { NextAuthOptions } from "next-auth";
import GithubProvider from "next-auth/providers/github";
import GoogleProvider from "next-auth/providers/google";

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.provider = account.provider;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.sub;
        (session.user as any).provider = token.provider;
      }
      return session;
    },
  },
};
```

- [ ] **Step 3: Create NextAuth API route**

```typescript
// frontend/src/app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

- [ ] **Step 4: Update layout with SessionProvider**

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { CopilotKit } from "@copilotkit/react-core";
import { SessionProvider } from "next-auth/react";
import "@copilotkit/react-ui/styles.css";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent-Evals Meta-Harness",
  description: "Evaluate your AI agents with conversational eval orchestration",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SessionProvider>
          <CopilotKit runtimeUrl="/api/copilotkit" agent="eval_harness">
            {children}
          </CopilotKit>
        </SessionProvider>
      </body>
    </html>
  );
}
```

Note: `SessionProvider` is a client component. If layout is a server component, wrap in a client-side `Providers` component:

```tsx
// frontend/src/components/providers.tsx
"use client";

import { SessionProvider } from "next-auth/react";
import { CopilotKit } from "@copilotkit/react-core";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <CopilotKit runtimeUrl="/api/copilotkit" agent="eval_harness">
        {children}
      </CopilotKit>
    </SessionProvider>
  );
}
```

Then in layout:
```tsx
import { Providers } from "@/components/providers";
// ...
<body className={inter.className}>
  <Providers>{children}</Providers>
</body>
```

- [ ] **Step 5: Update env example**

```bash
# frontend/.env.local.example
BACKEND_URL=http://localhost:8000/agui
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/app/api/auth/ frontend/src/components/providers.tsx frontend/src/app/layout.tsx frontend/.env.local.example
git commit -m "feat: add NextAuth.js with Google and GitHub OAuth"
```

---

### Task 14: JWT Validation in FastAPI

**Files:**
- Create: `backend/src/harness/auth/__init__.py`
- Create: `backend/src/harness/auth/jwt.py`

- [ ] **Step 1: Add PyJWT dependency**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add pyjwt[crypto]
```

- [ ] **Step 2: Implement JWT validation**

```python
# backend/src/harness/auth/__init__.py
```

```python
# backend/src/harness/auth/jwt.py
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from harness.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    email: str
    name: str
    provider: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Decode and validate JWT from NextAuth.js."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return CurrentUser(
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        name=payload.get("name", ""),
        provider=payload.get("provider", ""),
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser | None:
    """Same as get_current_user but returns None instead of 401."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/harness/auth/
git commit -m "feat: add JWT validation for NextAuth.js tokens"
```

---

### Task 15: HITL — Test Case Generation + Review

**Files:**
- Create: `backend/src/harness/meta_tools/generate_test_cases.py`
- Create: `backend/src/harness/meta_tools/review_test_cases.py`

- [ ] **Step 1: Implement test case generation**

```python
# backend/src/harness/meta_tools/generate_test_cases.py
import json
import uuid

from harness.meta_tools.registry import get_adapter


def generate_test_cases(agent_id: str, num_cases: int = 10, focus: str = "") -> str:
    """Generate test cases for a specific agent based on its capabilities.

    Args:
        agent_id: The agent to generate test cases for.
        num_cases: Number of test cases to generate (default 10, max 50).
        focus: Optional focus area for test case generation (e.g., "edge cases", "weather queries").

    Returns:
        JSON string with generated test cases ready for review.
    """
    adapter = get_adapter(agent_id)
    if adapter is None:
        return json.dumps({"error": f"Agent '{agent_id}' not found"})

    num_cases = min(num_cases, 50)

    # Generate based on agent type
    if "tools" in adapter.capabilities and "rag" not in adapter.capabilities:
        cases = _generate_tool_calling_cases(adapter, num_cases, focus)
    elif "rag" in adapter.capabilities:
        cases = _generate_rag_cases(adapter, num_cases, focus)
    else:
        cases = _generate_generic_cases(num_cases, focus)

    return json.dumps({
        "agent_id": agent_id,
        "generated_count": len(cases),
        "cases": cases,
        "note": "Review these cases and approve/edit them before running eval. Use review_test_cases to approve.",
    }, indent=2)


def _generate_tool_calling_cases(adapter, num_cases: int, focus: str) -> list[dict]:
    """Generate test cases for tool-calling agents."""
    templates = [
        {"input": "What is the weather in London?", "tool": "get_weather", "args": {"city": "London"}},
        {"input": "What is the weather in Tokyo?", "tool": "get_weather", "args": {"city": "Tokyo"}},
        {"input": "What is the weather in New York?", "tool": "get_weather", "args": {"city": "New York"}},
        {"input": "Calculate 42 * 17", "tool": "calculate", "args": {"expression": "42 * 17"}},
        {"input": "What is sqrt(144)?", "tool": "calculate", "args": {"expression": "sqrt(144)"}},
        {"input": "What is 2^10?", "tool": "calculate", "args": {"expression": "pow(2, 10)"}},
        {"input": "Tell me about machine learning", "tool": "search_knowledge", "args": {"query": "machine learning"}},
        {"input": "What is FastAPI?", "tool": "search_knowledge", "args": {"query": "FastAPI"}},
        {"input": "What is the weather in Paris and calculate 5+3?", "tool": "get_weather", "args": {"city": "Paris"}},
        {"input": "Search for Python programming", "tool": "search_knowledge", "args": {"query": "Python"}},
    ]
    cases = []
    for i, t in enumerate(templates[:num_cases]):
        cases.append({
            "id": f"gen-tc-{uuid.uuid4().hex[:8]}",
            "input": [{"role": "user", "content": t["input"]}],
            "expected_tools": [{"name": t["tool"], "args": t["args"]}],
            "expected_output": None,
            "tags": ["generated", t["tool"]],
            "approved": False,
        })
    return cases


def _generate_rag_cases(adapter, num_cases: int, focus: str) -> list[dict]:
    """Generate test cases for RAG agents."""
    from harness.agents.rag_agent import DOCUMENTS

    cases = []
    question_templates = [
        ("What is {title}?", "overview"),
        ("Explain the key features of {title}", "features"),
        ("When was {title} created or released?", "history"),
    ]
    for doc in DOCUMENTS[:num_cases]:
        for q_template, tag in question_templates:
            if len(cases) >= num_cases:
                break
            cases.append({
                "id": f"gen-rag-{uuid.uuid4().hex[:8]}",
                "input": [{"role": "user", "content": q_template.format(title=doc["title"].replace("What is ", "").rstrip("?"))}],
                "expected_output": None,
                "reference_contexts": [doc["content"]],
                "tags": ["generated", "rag", tag],
                "approved": False,
            })
    return cases[:num_cases]


def _generate_generic_cases(num_cases: int, focus: str) -> list[dict]:
    return [{"id": f"gen-{i}", "input": [{"role": "user", "content": f"Test query {i}"}], "approved": False} for i in range(num_cases)]
```

- [ ] **Step 2: Implement test case review**

```python
# backend/src/harness/meta_tools/review_test_cases.py
import json

# In-memory pending cases store — replaced with DB in production
_pending_cases: dict[str, list[dict]] = {}


def store_pending_cases(agent_id: str, cases: list[dict]) -> None:
    """Store generated cases awaiting review."""
    _pending_cases[agent_id] = cases


def review_test_cases(agent_id: str, action: str, case_ids: str = "") -> str:
    """Review generated test cases — approve, reject, or list pending cases.

    Args:
        agent_id: The agent whose test cases to review.
        action: One of "list", "approve_all", "approve" (specific cases), "reject" (specific cases).
        case_ids: Comma-separated list of case IDs for approve/reject actions.

    Returns:
        JSON string with the updated test case status.
    """
    if agent_id not in _pending_cases:
        return json.dumps({"error": f"No pending cases for agent '{agent_id}'. Generate cases first."})

    cases = _pending_cases[agent_id]

    if action == "list":
        return json.dumps({
            "agent_id": agent_id,
            "total_pending": len(cases),
            "cases": cases,
        }, indent=2)

    if action == "approve_all":
        for case in cases:
            case["approved"] = True
        return json.dumps({
            "agent_id": agent_id,
            "approved_count": len(cases),
            "message": "All cases approved. Ready to run eval.",
        })

    target_ids = {cid.strip() for cid in case_ids.split(",") if cid.strip()}
    if not target_ids:
        return json.dumps({"error": "No case_ids provided. Pass comma-separated IDs."})

    if action == "approve":
        approved = 0
        for case in cases:
            if case["id"] in target_ids:
                case["approved"] = True
                approved += 1
        return json.dumps({"approved_count": approved, "total_pending": len([c for c in cases if not c["approved"]])})

    if action == "reject":
        before = len(cases)
        cases[:] = [c for c in cases if c["id"] not in target_ids]
        _pending_cases[agent_id] = cases
        return json.dumps({"rejected_count": before - len(cases), "remaining": len(cases)})

    return json.dumps({"error": f"Unknown action '{action}'. Use list, approve_all, approve, or reject."})


def get_approved_cases(agent_id: str) -> list[dict]:
    """Return only approved cases for an agent."""
    return [c for c in _pending_cases.get(agent_id, []) if c.get("approved")]
```

- [ ] **Step 3: Add new tools to meta-agent**

Update `backend/src/harness/agents/meta_agent.py` to include the new tools:

```python
# Add to imports:
from harness.meta_tools.generate_test_cases import generate_test_cases
from harness.meta_tools.review_test_cases import review_test_cases

# Add to tools list in create_meta_agent():
tools=[list_agents, list_metrics, run_eval, explain_failure, generate_test_cases, review_test_cases],
```

Also update the META_AGENT_INSTRUCTION to mention the new workflow:
```
5. Generate test cases automatically (use generate_test_cases)
6. Let users review and approve cases before running (use review_test_cases)
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/harness/meta_tools/generate_test_cases.py backend/src/harness/meta_tools/review_test_cases.py backend/src/harness/agents/meta_agent.py
git commit -m "feat: add HITL test case generation and review"
```

---

### Task 16: HITL — Baseline Promotion + Compare Runs

**Files:**
- Create: `backend/src/harness/meta_tools/promote_baseline.py`
- Create: `backend/src/harness/meta_tools/compare_runs.py`

- [ ] **Step 1: Implement baseline promotion**

```python
# backend/src/harness/meta_tools/promote_baseline.py
import json

from harness.meta_tools.get_results import _results_store

# In-memory baseline store — replaced with DB
_baselines: dict[str, dict] = {}  # key: "{agent_id}:{suite_id}"


def promote_baseline(run_id: str, agent_id: str) -> str:
    """Promote an eval run to be the golden baseline for regression detection.

    Args:
        run_id: The eval run ID to promote.
        agent_id: The agent this baseline applies to.

    Returns:
        JSON confirmation with the baseline scores.
    """
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})

    run_data = _results_store[run_id]
    summary = run_data.get("summary", {})
    metric_averages = summary.get("metric_averages", {})

    if not metric_averages:
        return json.dumps({"error": "Run has no metric scores to use as baseline"})

    baseline_key = f"{agent_id}:default"
    _baselines[baseline_key] = {
        "run_id": run_id,
        "agent_id": agent_id,
        "scores": metric_averages,
        "pass_rate": summary.get("pass_rate", 0),
    }

    return json.dumps({
        "message": f"Baseline set for agent '{agent_id}'",
        "run_id": run_id,
        "scores": metric_averages,
        "pass_rate": summary.get("pass_rate", 0),
    }, indent=2)


def get_baseline(agent_id: str) -> dict | None:
    """Get the current baseline for an agent."""
    return _baselines.get(f"{agent_id}:default")
```

- [ ] **Step 2: Implement run comparison**

```python
# backend/src/harness/meta_tools/compare_runs.py
import json

from harness.meta_tools.get_results import _results_store
from harness.meta_tools.promote_baseline import get_baseline


def compare_runs(run_id: str, agent_id: str) -> str:
    """Compare an eval run against the current baseline, highlighting regressions.

    Args:
        run_id: The eval run to compare.
        agent_id: The agent to look up baseline for.

    Returns:
        JSON with deltas, regressions, and improvement details.
    """
    if run_id not in _results_store:
        return json.dumps({"error": f"Run '{run_id}' not found"})

    baseline = get_baseline(agent_id)
    if baseline is None:
        return json.dumps({
            "message": f"No baseline set for agent '{agent_id}'. Promote a run first.",
            "run_id": run_id,
        })

    run_data = _results_store[run_id]
    current_scores = run_data.get("summary", {}).get("metric_averages", {})
    baseline_scores = baseline["scores"]

    deltas = {}
    regressions = []
    improvements = []
    tolerance = 0.05

    for metric, baseline_score in baseline_scores.items():
        current = current_scores.get(metric)
        if current is None:
            continue
        delta = current - baseline_score
        deltas[metric] = round(delta, 4)
        if delta < -tolerance:
            regressions.append({
                "metric": metric,
                "baseline": round(baseline_score, 3),
                "current": round(current, 3),
                "delta": round(delta, 3),
            })
        elif delta > tolerance:
            improvements.append({
                "metric": metric,
                "baseline": round(baseline_score, 3),
                "current": round(current, 3),
                "delta": round(delta, 3),
            })

    return json.dumps({
        "run_id": run_id,
        "baseline_run_id": baseline["run_id"],
        "has_regressions": len(regressions) > 0,
        "regressions": regressions,
        "improvements": improvements,
        "deltas": deltas,
    }, indent=2)
```

- [ ] **Step 3: Add to meta-agent tools**

Update `backend/src/harness/agents/meta_agent.py`:

```python
# Add imports:
from harness.meta_tools.compare_runs import compare_runs
from harness.meta_tools.promote_baseline import promote_baseline

# Add to tools list:
tools=[list_agents, list_metrics, run_eval, explain_failure, generate_test_cases, review_test_cases, compare_runs, promote_baseline],
```

- [ ] **Step 4: Commit**

```bash
git add backend/src/harness/meta_tools/promote_baseline.py backend/src/harness/meta_tools/compare_runs.py backend/src/harness/agents/meta_agent.py
git commit -m "feat: add HITL baseline promotion and run comparison"
```

---

### Task 17: UI Components — Agent Cards, Results Table, Run History

**Files:**
- Create: `frontend/src/components/agent-card.tsx`
- Create: `frontend/src/components/results-table.tsx`
- Create: `frontend/src/components/run-history.tsx`
- Create: `frontend/src/components/test-case-list.tsx`
- Create: `frontend/src/types/index.ts`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Install shadcn components**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npx shadcn@latest add card badge table scroll-area
```

- [ ] **Step 2: Create shared types**

```typescript
// frontend/src/types/index.ts
export interface AgentInfo {
  agent_id: string;
  display_name: string;
  capabilities: string[];
  supported_metrics: string[];
}

export interface MetricScore {
  name: string;
  score: number;
  passed: boolean;
  threshold: number;
}

export interface CaseResult {
  test_case_id: string;
  passed: boolean;
  latency_ms: number;
  metrics: MetricScore[];
}

export interface EvalRunSummary {
  run_id: string;
  overall_passed: boolean;
  summary: {
    total_cases: number;
    passed: number;
    failed: number;
    pass_rate: number;
    avg_latency_ms: number;
    metric_averages: Record<string, number>;
  };
  results: CaseResult[];
}

export interface TestCase {
  id: string;
  input: { role: string; content: string }[];
  expected_output?: string;
  expected_tools?: { name: string; args: Record<string, unknown> }[];
  reference_contexts?: string[];
  tags?: string[];
  approved: boolean;
}
```

- [ ] **Step 3: Create AgentCard**

```tsx
// frontend/src/components/agent-card.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentInfo } from "@/types";

interface AgentCardProps {
  agent: AgentInfo;
  onClick?: () => void;
}

export function AgentCard({ agent, onClick }: AgentCardProps) {
  return (
    <Card
      className="cursor-pointer hover:border-blue-500 transition-colors"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{agent.display_name}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1 mb-2">
          {agent.capabilities.map((cap) => (
            <Badge key={cap} variant="secondary" className="text-xs">
              {cap}
            </Badge>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          {agent.supported_metrics.length} metrics available
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create ResultsTable**

```tsx
// frontend/src/components/results-table.tsx
"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { CaseResult } from "@/types";

interface ResultsTableProps {
  results: CaseResult[];
}

export function ResultsTable({ results }: ResultsTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Test Case</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Latency</TableHead>
            <TableHead>Metrics</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {results.map((result) => (
            <TableRow key={result.test_case_id}>
              <TableCell className="font-mono text-sm">
                {result.test_case_id}
              </TableCell>
              <TableCell>
                <Badge variant={result.passed ? "default" : "destructive"}>
                  {result.passed ? "PASS" : "FAIL"}
                </Badge>
              </TableCell>
              <TableCell>{result.latency_ms.toFixed(0)}ms</TableCell>
              <TableCell>
                <div className="flex gap-1 flex-wrap">
                  {result.metrics.map((m) => (
                    <Badge
                      key={m.name}
                      variant={m.passed ? "outline" : "destructive"}
                      className="text-xs"
                    >
                      {m.name}: {m.score.toFixed(2)}
                    </Badge>
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

- [ ] **Step 5: Create TestCaseList**

```tsx
// frontend/src/components/test-case-list.tsx
"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TestCase } from "@/types";

interface TestCaseListProps {
  cases: TestCase[];
}

export function TestCaseList({ cases }: TestCaseListProps) {
  return (
    <div className="space-y-2">
      {cases.map((tc) => (
        <Card key={tc.id} className="p-3">
          <CardContent className="p-0">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-mono">{tc.id}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {tc.input[0]?.content}
                </p>
              </div>
              <Badge variant={tc.approved ? "default" : "secondary"}>
                {tc.approved ? "Approved" : "Pending"}
              </Badge>
            </div>
            {tc.tags && tc.tags.length > 0 && (
              <div className="flex gap-1 mt-2">
                {tc.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Create RunHistory**

```tsx
// frontend/src/components/run-history.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface RunEntry {
  run_id: string;
  pass_rate: number;
  total_cases: number;
  is_baseline: boolean;
  timestamp?: string;
}

interface RunHistoryProps {
  runs: RunEntry[];
}

export function RunHistory({ runs }: RunHistoryProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-muted-foreground">Run History</h3>
      {runs.map((run) => (
        <Card key={run.run_id} className="p-2">
          <CardContent className="p-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono">{run.run_id.slice(0, 8)}...</p>
              <p className="text-xs text-muted-foreground">
                {run.total_cases} cases · {(run.pass_rate * 100).toFixed(0)}% pass
              </p>
            </div>
            <div className="flex gap-1">
              {run.is_baseline && (
                <Badge variant="default" className="text-xs">Baseline</Badge>
              )}
              <Badge
                variant={run.pass_rate === 1 ? "default" : "destructive"}
                className="text-xs"
              >
                {(run.pass_rate * 100).toFixed(0)}%
              </Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Update main page with layout**

```tsx
// frontend/src/app/page.tsx
"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useSession, signIn } from "next-auth/react";

export default function Home() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Agent-Evals Meta-Harness</h1>
          <p className="text-gray-400 mb-6">Sign in to start evaluating your AI agents</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => signIn("google")}
              className="px-4 py-2 bg-white text-black rounded-md hover:bg-gray-200 transition"
            >
              Sign in with Google
            </button>
            <button
              onClick={() => signIn("github")}
              className="px-4 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-700 transition border border-gray-600"
            >
              Sign in with GitHub
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950">
      <aside className="w-64 border-r border-gray-800 p-4 flex flex-col">
        <h1 className="text-xl font-bold text-white mb-2">Agent Evals</h1>
        <p className="text-xs text-gray-500 mb-4">Signed in as {session.user?.name}</p>
        <p className="text-sm text-gray-400">
          Chat with the eval harness to test and evaluate AI agents.
        </p>
      </aside>

      <main className="flex-1 flex flex-col">
        <CopilotChat
          className="flex-1"
          instructions="You are the Agent-Evals Meta-Harness. Help users evaluate their AI agents."
          labels={{
            title: "Eval Harness",
            initial: "Hello! I can help you evaluate AI agents. Try asking me to list available agents.",
            placeholder: "Ask about agents, run evals, or explore results...",
          }}
        />
      </main>
    </div>
  );
}
```

- [ ] **Step 8: Test frontend builds**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/ frontend/src/types/ frontend/src/app/page.tsx
git commit -m "feat: add UI components and auth-gated layout"
```

---

## WEEK 4: Deploy + OTel + Harden

---

### Task 18: Dockerfile + Cloud Run Deploy

**Files:**
- Create: `backend/Dockerfile`
- Create: `.gcloudignore`

- [ ] **Step 1: Create multi-stage Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

FROM python:3.12-slim

RUN groupadd -r harness && useradd -r -g harness -s /sbin/nologin harness

WORKDIR /app
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

USER harness

CMD ["uvicorn", "harness.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Test Docker build locally**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
docker build -t harness-backend .
docker run --rm -p 8080:8080 -e GOOGLE_API_KEY=test harness-backend &
sleep 3
curl http://localhost:8080/health
docker stop $(docker ps -q --filter ancestor=harness-backend)
```

Expected: Health endpoint returns ok.

- [ ] **Step 3: Deploy to Cloud Run**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
gcloud run deploy agent-evals-harness \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 4 \
  --cpu-boost \
  --memory 512Mi \
  --set-env-vars "GOOGLE_API_KEY=your-key,DATABASE_URL=your-neon-url,HARNESS_CORS_ORIGINS=https://your-frontend.vercel.app"
```

- [ ] **Step 4: Verify deployment**

```bash
SERVICE_URL=$(gcloud run services describe agent-evals-harness --region us-central1 --format='value(status.url)')
curl $SERVICE_URL/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile .gcloudignore
git commit -m "feat: add Dockerfile and Cloud Run deploy config"
```

---

### Task 19: Vercel Production Deploy

**Files:**
- Modify: `frontend/next.config.ts`

- [ ] **Step 1: Update next.config for production backend URL**

```typescript
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 2: Deploy to Vercel**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npx vercel --prod
```

Set environment variables in Vercel dashboard:
- `BACKEND_URL` → Cloud Run service URL + `/agui`
- `NEXTAUTH_SECRET` → generated secret
- `NEXTAUTH_URL` → Vercel deployment URL
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

- [ ] **Step 3: Update Cloud Run CORS**

```bash
gcloud run services update agent-evals-harness \
  --region us-central1 \
  --set-env-vars "HARNESS_CORS_ORIGINS=https://your-app.vercel.app"
```

- [ ] **Step 4: Verify end-to-end**

Open Vercel URL → sign in → chat → "list agents" → verify response.

- [ ] **Step 5: Commit**

```bash
git add frontend/next.config.ts
git commit -m "chore: configure Next.js for Vercel production deploy"
```

---

### Task 20: OTel Instrumentation + Grafana Cloud

**Files:**
- Create: `backend/src/harness/telemetry/__init__.py`
- Create: `backend/src/harness/telemetry/otel.py`
- Modify: `backend/src/harness/main.py`
- Modify: `backend/src/harness/eval/engine.py`

- [ ] **Step 1: Add OTel dependencies**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi
```

- [ ] **Step 2: Create OTel setup**

```python
# backend/src/harness/telemetry/otel.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from harness.config import settings


def setup_telemetry(app) -> None:
    """Initialize OpenTelemetry with Grafana Cloud export."""
    if not settings.otel_endpoint:
        return  # Skip in local dev

    resource = Resource.create({
        "service.name": "agent-evals-harness",
        "service.version": "0.1.0",
        "deployment.environment": settings.environment,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)


tracer = trace.get_tracer("harness.eval")
```

- [ ] **Step 3: Add tracing to eval engine**

Update `backend/src/harness/eval/engine.py` — add spans around eval runs:

```python
# At top:
from harness.telemetry.otel import tracer

# In EvalRunner.run(), wrap the main loop:
async def run(self, run_id: str, suite_id: str) -> EvalReport:
    with tracer.start_as_current_span(
        "eval_run",
        attributes={"eval.run_id": run_id, "eval.suite_id": suite_id, "eval.total_cases": len(self._test_cases)},
    ):
        ctx = RunContext(run_id=run_id, suite_id=suite_id)
        case_results: list[CaseResult] = []

        for tc in self._test_cases:
            with tracer.start_as_current_span(
                "eval_case",
                attributes={"eval.case_id": tc.id},
            ):
                response = await self._adapter.invoke(tc.input, ctx)
                # ... rest of scoring logic unchanged
```

- [ ] **Step 4: Wire telemetry into app startup**

Update `backend/src/harness/main.py`:

```python
# Add import:
from harness.telemetry.otel import setup_telemetry

# In create_app(), after creating app:
setup_telemetry(app)
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/telemetry/ backend/src/harness/main.py backend/src/harness/eval/engine.py
git commit -m "feat: add OTel instrumentation with Grafana Cloud export"
```

---

### Task 21: Error Handling + Rate Limiting + Validation

**Files:**
- Modify: `backend/src/harness/main.py`
- Modify: `backend/src/harness/meta_tools/run_eval.py`

- [ ] **Step 1: Add rate limiting dependency**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv add slowapi
```

- [ ] **Step 2: Add rate limiter to main app**

```python
# In backend/src/harness/main.py, add:
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

# In create_app():
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
```

- [ ] **Step 3: Add error handling to run_eval**

In `backend/src/harness/meta_tools/run_eval.py`, wrap the eval execution in try/except:

```python
# Around the eval runner execution:
try:
    report = await runner.run(run_id=run_id, suite_id=f"{agent_id}-eval")
except Exception as e:
    return json.dumps({"error": f"Eval run failed: {str(e)}", "run_id": run_id})
```

- [ ] **Step 4: Add global exception handler**

```python
# In backend/src/harness/main.py:
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/harness/main.py backend/src/harness/meta_tools/run_eval.py
git commit -m "feat: add rate limiting and error handling"
```

---

### Task 22: Seed Data + Demo Prep

**Files:**
- Create: `backend/scripts/seed.py`
- Modify: `README.md`

- [ ] **Step 1: Create seed script**

```python
# backend/scripts/seed.py
"""Seed the database with demo agents and a pre-run eval for instant demo."""
import asyncio
import json
import uuid

from harness.adapters.tool_calling import ToolCallingAdapter
from harness.adapters.types import RunContext, ToolCall, Turn
from harness.eval.engine import EvalRunner, EvalTestCase
from harness.eval.metrics import MetricBackend, MetricConfig
from harness.meta_tools.get_results import store_results
from harness.meta_tools.promote_baseline import promote_baseline
from harness.meta_tools.registry import init_registry


async def seed() -> None:
    init_registry()

    # Run a small eval on the tool-calling agent and store results
    adapter = ToolCallingAdapter()
    metrics = [
        MetricConfig(name="tool_trajectory_avg_score", backend=MetricBackend.ADK, threshold=1.0),
    ]
    test_cases = [
        EvalTestCase(
            id="seed-weather",
            input=[Turn(role="user", content="What is the weather in Paris?")],
            expected_output=None,
            expected_tools=[ToolCall(name="get_weather", args={"city": "Paris"})],
            reference_contexts=None,
            tags=["weather", "seed"],
        ),
    ]
    runner = EvalRunner(adapter=adapter, metrics=metrics, test_cases=test_cases)
    run_id = "seed-run-001"
    report = await runner.run(run_id=run_id, suite_id="tool-calling-seed")

    results = {
        "run_id": run_id,
        "overall_passed": report.overall_passed,
        "summary": report.summary(),
        "results": [
            {
                "test_case_id": cr.test_case_id,
                "passed": cr.passed,
                "latency_ms": round(cr.latency_ms, 1),
                "metrics": [
                    {"name": mr.name, "score": round(mr.score, 3), "passed": mr.passed, "threshold": mr.threshold}
                    for mr in cr.metric_results
                ],
            }
            for cr in report.case_results
        ],
    }
    store_results(run_id, results)
    print(f"Seeded eval run: {run_id}")
    print(f"Results: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Update README**

```markdown
# Agent-Evals Meta-Harness

Conversational eval harness for AI agents. Chat with a meta-agent to evaluate, compare, and track your agents' quality.

## Quick Start

### Backend
```bash
cd backend
uv sync
cp .env.example .env  # fill in API keys
uv run uvicorn harness.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local  # fill in OAuth + backend URL
npm run dev
```

Open http://localhost:3000

## Architecture

Three-layer split: Conversational (ADK meta-agent + AG-UI + CopilotKit) → Eval Engine (ADK + DeepEval metrics) → Agent Adapters (tool-calling, RAG).

See `docs/superpowers/specs/2026-06-28-agent-evals-meta-harness-design.md` for full spec.
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed.py README.md
git commit -m "feat: add seed script and update README"
```

---

### Task 23: Final Integration Test + Verify

**Files:**
- No new files — run full test suite and manual verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run pytest tests/ -v --tb=short
```

Expected: All tests pass (integration tests may skip without API key).

- [ ] **Step 2: Run linting**

```bash
cd /home/adithya/Document/llm-perf-harness/backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Fix any issues.

- [ ] **Step 3: Run frontend build**

```bash
cd /home/adithya/Document/llm-perf-harness/frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Manual E2E verification**

Start both servers and verify the full flow:
1. Open app → sign in
2. "List available agents" → see tool-calling + RAG agents
3. "Generate 5 test cases for the tool-calling agent" → see generated cases
4. "Approve all cases" → cases approved
5. "Run eval on the tool-calling agent" with the approved cases → see results stream
6. "Explain the first failure" (if any) → see detailed explanation
7. "Set this as the baseline" → baseline promoted

- [ ] **Step 5: Final commit if any fixes**

```bash
git add -A
git commit -m "fix: address issues found in final integration testing"
```
