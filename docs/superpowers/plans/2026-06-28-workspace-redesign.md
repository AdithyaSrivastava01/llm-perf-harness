# Workspace Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the harness around persistent workspaces — replace all in-memory stores with DB persistence, add Workspace/AgentSpec models, trace timeline, spec-aware scoring, and a full sidebar-based workspace UI.

**Architecture:** Workspace is the top-level container scoping all data. DB query service layer (`db/queries.py`) replaces in-memory dicts. Meta-tools route through queries. Frontend moves from single-page chat to multi-route workspace UI with sidebar navigation.

**Tech Stack:** SQLAlchemy async (existing), Alembic migrations, FastAPI routes, Next.js App Router, Tailwind + shadcn/ui.

**Spec:** `docs/superpowers/specs/2026-06-28-workspace-redesign.md`

---

## File Structure

```
backend/src/harness/
├── db/
│   ├── models.py               # MODIFY: add Workspace, AgentSpec, new FKs
│   ├── queries.py              # NEW: all async DB query functions
│   └── engine.py               # existing, unchanged
├── api/
│   ├── workspace_routes.py     # NEW: workspace CRUD
│   ├── agent_routes.py         # NEW: agent connection, spec upload
│   ├── quick_eval_routes.py    # MODIFY: scope to workspace
│   └── health.py               # unchanged
├── eval/
│   ├── trace_builder.py        # NEW: build TraceSpan from raw events
│   ├── spec_scorer.py          # NEW: spec adherence metric
│   ├── engine.py               # MODIFY: include trace spans
│   ├── quick_eval.py           # MODIFY: workspace-scoped, persist results
│   └── metrics.py              # MODIFY: add spec_adherence metric
├── meta_tools/
│   ├── *.py                    # MODIFY: all tools use DB queries + workspace_id
│   └── registry.py             # MODIFY: load from DB instead of in-memory
├── main.py                     # MODIFY: mount new routes
└── config.py                   # MODIFY: add workspace settings

backend/tests/
├── unit/
│   ├── test_workspace_models.py    # NEW
│   ├── test_queries.py             # NEW
│   ├── test_trace_builder.py       # NEW
│   └── test_spec_scorer.py         # NEW
├── integration/
│   └── test_workspace_flow.py      # NEW: full workspace lifecycle
└── e2e/
    └── test_workspace_api.py       # NEW: API endpoint tests

frontend/src/
├── app/
│   ├── login/page.tsx              # NEW
│   ├── workspaces/page.tsx         # NEW
│   ├── w/[id]/
│   │   ├── page.tsx                # NEW: workspace dashboard
│   │   ├── layout.tsx              # NEW: sidebar layout
│   │   ├── agents/
│   │   │   ├── [agentId]/
│   │   │   │   ├── page.tsx        # NEW: agent detail
│   │   │   │   └── runs/
│   │   │   │       └── [runId]/page.tsx  # NEW: run detail
│   │   │   └── connect/page.tsx    # NEW: connect agent flow
│   │   └── settings/page.tsx       # NEW: workspace settings
│   └── page.tsx                    # MODIFY: redirect to /workspaces
├── components/
│   ├── sidebar.tsx                 # NEW
│   ├── agent-card.tsx              # MODIFY: add sparkline, baseline
│   ├── trace-timeline.tsx          # NEW
│   ├── spec-editor.tsx             # NEW
│   ├── run-table.tsx               # NEW
│   ├── baseline-compare.tsx        # NEW
│   └── report-card.tsx             # existing, keep
└── lib/
    └── api.ts                      # NEW: typed API client
```

---

## Task 1: Workspace + AgentSpec Models + Migration

**Files:**
- Modify: `backend/src/harness/db/models.py`
- Create: `backend/tests/unit/test_workspace_models.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_workspace_models.py
import uuid
from harness.db.models import AgentSpec, Workspace


def test_workspace_fields() -> None:
    ws = Workspace(
        name="Production", owner_id=uuid.uuid4(), agent_limit=3, tier="free",
    )
    assert ws.name == "Production"
    assert ws.tier == "free"
    assert ws.agent_limit == 3


def test_workspace_default_settings() -> None:
    ws = Workspace(name="Test", owner_id=uuid.uuid4())
    assert ws.tier == "free"
    assert ws.agent_limit == 3


def test_agent_spec_fields() -> None:
    spec = AgentSpec(
        agent_id=uuid.uuid4(), content="name: test", parsed={"name": "test"}, version=1,
    )
    assert spec.content == "name: test"
    assert spec.parsed["name"] == "test"
    assert spec.version == 1
```

- [ ] **Step 2: Run test to verify failure**
```bash
cd backend && uv run pytest tests/unit/test_workspace_models.py -v
```

- [ ] **Step 3: Add models to db/models.py**

Add `Workspace` class after `User`:

```python
class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_limit: Mapped[int] = mapped_column(default=3)
    tier: Mapped[str] = mapped_column(String, nullable=False, default="free")
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_workspaces_owner", "owner_id"),)
```

Add `AgentSpec` class at the end:

```python
class AgentSpec(Base):
    __tablename__ = "agent_specs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_agents.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parsed: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Add `workspace_id` FK to `ConnectedAgent`:
```python
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
```
And index: `__table_args__ = (Index("ix_connected_agents_workspace", "workspace_id"),)`

Add `workspace_id` to `EvalRun` (nullable for migration compatibility):
```python
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True)
```

Add `trace_spans` to `EvalResult`:
```python
    trace_spans: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

Add `spec_version` to `EvalRun`:
```python
    spec_version: Mapped[int | None] = mapped_column(nullable=True)
```

- [ ] **Step 4: Run tests**
```bash
cd backend && uv run pytest tests/unit/test_workspace_models.py -v
```

- [ ] **Step 5: Generate migration**
```bash
cd backend && uv run alembic revision --autogenerate -m "add workspace agentspec trace_spans"
```

- [ ] **Step 6: Commit**
```bash
git add backend/src/harness/db/models.py backend/tests/unit/test_workspace_models.py backend/alembic/
git commit -m "feat: add Workspace, AgentSpec models and workspace FKs"
```

---

## Task 2: DB Query Service

**Files:**
- Create: `backend/src/harness/db/queries.py`
- Create: `backend/tests/unit/test_queries.py`

- [ ] **Step 1: Write test for workspace queries**

```python
# backend/tests/unit/test_queries.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from harness.db.queries import (
    WorkspaceCreate, AgentCreate, workspace_to_dict, agent_to_dict,
)


def test_workspace_create_schema() -> None:
    ws = WorkspaceCreate(name="Test", owner_id=uuid.uuid4())
    assert ws.name == "Test"
    assert ws.tier == "free"
    assert ws.agent_limit == 3


def test_agent_create_schema() -> None:
    ac = AgentCreate(
        workspace_id=uuid.uuid4(), endpoint_url="https://example.com/v1/chat/completions",
        schema_type="openai", display_name="My Agent",
    )
    assert ac.schema_type == "openai"
    assert ac.display_name == "My Agent"
```

- [ ] **Step 2: Implement queries module**

```python
# backend/src/harness/db/queries.py
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from harness.db.models import (
    AgentSpec, Baseline, ConnectedAgent, EvalResult, EvalRun, EvalSuite,
    TestCase as TestCaseModel, Workspace,
)


# --- Input schemas ---

@dataclass
class WorkspaceCreate:
    name: str
    owner_id: uuid.UUID
    tier: str = "free"
    agent_limit: int = 3


@dataclass
class AgentCreate:
    workspace_id: uuid.UUID
    endpoint_url: str
    schema_type: str = "openai"
    display_name: str | None = None
    auth_header_enc: str | None = None
    detected_capabilities: list[str] | None = None
    confirmed_capabilities: list[str] | None = None
    custom_schema: dict | None = None


# --- Helpers ---

def workspace_to_dict(ws: Workspace) -> dict[str, Any]:
    return {"id": str(ws.id), "name": ws.name, "owner_id": str(ws.owner_id),
            "tier": ws.tier, "agent_limit": ws.agent_limit, "created_at": ws.created_at.isoformat() if ws.created_at else None}


def agent_to_dict(a: ConnectedAgent) -> dict[str, Any]:
    return {"id": str(a.id), "workspace_id": str(a.workspace_id), "endpoint_url": a.endpoint_url,
            "schema_type": a.schema_type, "display_name": a.display_name,
            "detected_capabilities": a.detected_capabilities, "confirmed_capabilities": a.confirmed_capabilities,
            "created_at": a.created_at.isoformat() if a.created_at else None}


# --- Workspace CRUD ---

async def create_workspace(session: AsyncSession, data: WorkspaceCreate) -> Workspace:
    ws = Workspace(name=data.name, owner_id=data.owner_id, tier=data.tier, agent_limit=data.agent_limit)
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return ws


async def get_workspace(session: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    return await session.get(Workspace, workspace_id)


async def list_workspaces(session: AsyncSession, owner_id: uuid.UUID) -> list[Workspace]:
    result = await session.execute(select(Workspace).where(Workspace.owner_id == owner_id))
    return list(result.scalars().all())


# --- Agent CRUD (scoped to workspace) ---

async def connect_agent(session: AsyncSession, data: AgentCreate) -> ConnectedAgent:
    # Check agent limit
    result = await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.workspace_id == data.workspace_id)
    )
    existing = list(result.scalars().all())
    ws = await get_workspace(session, data.workspace_id)
    if ws and len(existing) >= ws.agent_limit:
        raise ValueError(f"Agent limit ({ws.agent_limit}) reached for this workspace")

    agent = ConnectedAgent(
        workspace_id=data.workspace_id, endpoint_url=data.endpoint_url,
        schema_type=data.schema_type, display_name=data.display_name,
        auth_header_enc=data.auth_header_enc, detected_capabilities=data.detected_capabilities,
        confirmed_capabilities=data.confirmed_capabilities, custom_schema=data.custom_schema,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    return agent


async def get_agents(session: AsyncSession, workspace_id: uuid.UUID) -> list[ConnectedAgent]:
    result = await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.workspace_id == workspace_id)
    )
    return list(result.scalars().all())


async def get_agent(session: AsyncSession, workspace_id: uuid.UUID, agent_id: uuid.UUID) -> ConnectedAgent | None:
    result = await session.execute(
        select(ConnectedAgent).where(ConnectedAgent.workspace_id == workspace_id, ConnectedAgent.id == agent_id)
    )
    return result.scalar_one_or_none()


# --- Eval Run operations ---

async def save_eval_run(
    session: AsyncSession, workspace_id: uuid.UUID, agent_id: uuid.UUID,
    run_id: uuid.UUID, summary: dict, status: str = "completed",
    spec_version: int | None = None,
) -> EvalRun:
    run = EvalRun(
        id=run_id, suite_id=agent_id, triggered_by=workspace_id,  # reuse fields
        workspace_id=workspace_id, status=status, summary=summary,
        spec_version=spec_version, started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_eval_runs(session: AsyncSession, workspace_id: uuid.UUID, agent_id: uuid.UUID | None = None) -> list[EvalRun]:
    stmt = select(EvalRun).where(EvalRun.workspace_id == workspace_id)
    if agent_id:
        stmt = stmt.where(EvalRun.suite_id == agent_id)
    stmt = stmt.order_by(EvalRun.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_eval_run(session: AsyncSession, run_id: uuid.UUID) -> EvalRun | None:
    return await session.get(EvalRun, run_id)


# --- Baseline operations ---

async def promote_baseline_db(
    session: AsyncSession, workspace_id: uuid.UUID, agent_id: uuid.UUID,
    run_id: uuid.UUID, scores: dict, promoted_by: uuid.UUID,
) -> Baseline:
    # Deactivate existing baselines for this agent
    await session.execute(
        update(Baseline).where(
            Baseline.agent_id == agent_id, Baseline.active == True
        ).values(active=False)
    )
    baseline = Baseline(
        agent_id=agent_id, suite_id=agent_id, run_id=run_id,
        scores=scores, promoted_by=promoted_by, active=True,
    )
    session.add(baseline)
    await session.commit()
    await session.refresh(baseline)
    return baseline


async def get_active_baseline(session: AsyncSession, agent_id: uuid.UUID) -> Baseline | None:
    result = await session.execute(
        select(Baseline).where(Baseline.agent_id == agent_id, Baseline.active == True)
    )
    return result.scalar_one_or_none()


# --- Spec operations ---

async def save_spec(session: AsyncSession, agent_id: uuid.UUID, content: str, parsed: dict) -> AgentSpec:
    # Get next version
    result = await session.execute(
        select(AgentSpec).where(AgentSpec.agent_id == agent_id).order_by(AgentSpec.version.desc())
    )
    latest = result.scalar_one_or_none()
    version = (latest.version + 1) if latest else 1

    spec = AgentSpec(agent_id=agent_id, content=content, parsed=parsed, version=version)
    session.add(spec)
    await session.commit()
    await session.refresh(spec)
    return spec


async def get_latest_spec(session: AsyncSession, agent_id: uuid.UUID) -> AgentSpec | None:
    result = await session.execute(
        select(AgentSpec).where(AgentSpec.agent_id == agent_id).order_by(AgentSpec.version.desc())
    )
    return result.scalar_one_or_none()
```

- [ ] **Step 3: Run tests**
```bash
cd backend && uv run pytest tests/unit/test_queries.py -v
```

- [ ] **Step 4: Commit**
```bash
git add backend/src/harness/db/queries.py backend/tests/unit/test_queries.py
git commit -m "feat: add DB query service for workspace-scoped operations"
```

---

## Task 3: Trace Builder

**Files:**
- Create: `backend/src/harness/eval/trace_builder.py`
- Create: `backend/tests/unit/test_trace_builder.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_trace_builder.py
from harness.adapters.types import AgentResponse, TokenUsage, ToolCall
from harness.eval.trace_builder import TraceSpan, build_trace_from_response


def test_build_trace_text_only() -> None:
    resp = AgentResponse(
        output="Hello!", tool_calls=[], retrieved_contexts=[],
        latency_ms=100.0, token_usage=TokenUsage(input_tokens=10, output_tokens=5), raw_events=[],
    )
    spans = build_trace_from_response(resp)
    assert len(spans) >= 1
    assert spans[-1].type == "llm_call"
    assert spans[-1].output["text"] == "Hello!"


def test_build_trace_with_tools() -> None:
    resp = AgentResponse(
        output="Weather is sunny.", tool_calls=[ToolCall(name="get_weather", args={"city": "Paris"})],
        retrieved_contexts=[], latency_ms=200.0,
        token_usage=TokenUsage(input_tokens=15, output_tokens=10), raw_events=[],
    )
    spans = build_trace_from_response(resp)
    tool_spans = [s for s in spans if s.type == "tool_call"]
    assert len(tool_spans) == 1
    assert tool_spans[0].name == "get_weather"
    assert tool_spans[0].input == {"city": "Paris"}


def test_trace_span_to_dict() -> None:
    span = TraceSpan(type="llm_call", name="LLM", start_ms=0, duration_ms=100,
                     input={"text": "hi"}, output={"text": "hello"}, metadata={})
    d = span.to_dict()
    assert d["type"] == "llm_call"
    assert d["duration_ms"] == 100
```

- [ ] **Step 2: Run test to verify failure**
```bash
cd backend && uv run pytest tests/unit/test_trace_builder.py -v
```

- [ ] **Step 3: Implement trace builder**

```python
# backend/src/harness/eval/trace_builder.py
from dataclasses import dataclass, field
from typing import Any

from harness.adapters.types import AgentResponse


@dataclass
class TraceSpan:
    type: str           # "llm_call" | "tool_call" | "scoring"
    name: str
    start_ms: float
    duration_ms: float
    input: dict
    output: dict
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type, "name": self.name,
            "start_ms": self.start_ms, "duration_ms": self.duration_ms,
            "input": self.input, "output": self.output, "metadata": self.metadata,
        }


def build_trace_from_response(resp: AgentResponse) -> list[TraceSpan]:
    """Build a trace timeline from an AgentResponse."""
    spans: list[TraceSpan] = []
    elapsed = 0.0

    if resp.tool_calls:
        # Initial LLM call that decided to use tools
        tool_decision_ms = resp.latency_ms * 0.3
        spans.append(TraceSpan(
            type="llm_call", name="LLM", start_ms=0, duration_ms=tool_decision_ms,
            input={"text": "(user message)"}, output={"action": "tool_call"},
            metadata={"tokens": resp.token_usage.input_tokens},
        ))
        elapsed = tool_decision_ms

        # Tool calls
        tool_ms = resp.latency_ms * 0.2 / max(len(resp.tool_calls), 1)
        for tc in resp.tool_calls:
            spans.append(TraceSpan(
                type="tool_call", name=tc.name, start_ms=elapsed, duration_ms=tool_ms,
                input=tc.args, output={}, metadata={},
            ))
            elapsed += tool_ms

        # Final LLM call with tool results
        final_ms = resp.latency_ms - elapsed
        spans.append(TraceSpan(
            type="llm_call", name="LLM", start_ms=elapsed, duration_ms=max(final_ms, 0),
            input={"tool_results": len(resp.tool_calls)}, output={"text": resp.output},
            metadata={"tokens": resp.token_usage.output_tokens},
        ))
    else:
        # Simple LLM call
        spans.append(TraceSpan(
            type="llm_call", name="LLM", start_ms=0, duration_ms=resp.latency_ms,
            input={"text": "(user message)"}, output={"text": resp.output},
            metadata={"tokens": resp.token_usage.total_tokens},
        ))

    return spans
```

- [ ] **Step 4: Run tests**
```bash
cd backend && uv run pytest tests/unit/test_trace_builder.py -v
```

- [ ] **Step 5: Commit**
```bash
git add backend/src/harness/eval/trace_builder.py backend/tests/unit/test_trace_builder.py
git commit -m "feat: add trace builder for agent execution timeline"
```

---

## Task 4: Spec Scorer

**Files:**
- Create: `backend/src/harness/eval/spec_scorer.py`
- Create: `backend/tests/unit/test_spec_scorer.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/unit/test_spec_scorer.py
from harness.eval.spec_scorer import parse_spec_yaml, generate_spec_test_cases, get_tool_coverage


def test_parse_spec_yaml() -> None:
    yaml_content = """
name: "Test Agent"
description: "A test agent"
expected_tools:
  - name: search
    description: "Search the web"
constraints:
  - "Never share passwords"
  - "Always cite sources"
example_interactions:
  - input: "Find info about Python"
    expected_behavior: "Use search tool"
"""
    parsed = parse_spec_yaml(yaml_content)
    assert parsed["name"] == "Test Agent"
    assert len(parsed["expected_tools"]) == 1
    assert len(parsed["constraints"]) == 2
    assert len(parsed["example_interactions"]) == 1


def test_generate_spec_test_cases() -> None:
    spec = {
        "expected_tools": [{"name": "lookup_order", "description": "Look up order"}],
        "constraints": ["Always ask for order ID"],
        "example_interactions": [{"input": "Where is my order?", "expected_behavior": "Ask for order ID"}],
    }
    cases = generate_spec_test_cases(spec, max_cases=5)
    assert len(cases) > 0
    assert all("input" in c for c in cases)


def test_get_tool_coverage() -> None:
    spec_tools = [{"name": "search"}, {"name": "calculate"}, {"name": "email"}]
    used_tools = {"search", "calculate"}
    coverage = get_tool_coverage(spec_tools, used_tools)
    assert coverage["covered"] == ["calculate", "search"]
    assert coverage["missing"] == ["email"]
    assert coverage["coverage_pct"] == 2 / 3
```

- [ ] **Step 2: Run test to verify failure**
```bash
cd backend && uv run pytest tests/unit/test_spec_scorer.py -v
```

- [ ] **Step 3: Implement spec scorer**

```python
# backend/src/harness/eval/spec_scorer.py
import yaml
from typing import Any


def parse_spec_yaml(content: str) -> dict[str, Any]:
    """Parse a YAML agent spec file into structured dict."""
    parsed = yaml.safe_load(content)
    if not isinstance(parsed, dict):
        raise ValueError("Spec must be a YAML mapping")
    # Normalize
    parsed.setdefault("name", "Unnamed Agent")
    parsed.setdefault("description", "")
    parsed.setdefault("expected_tools", [])
    parsed.setdefault("constraints", [])
    parsed.setdefault("example_interactions", [])
    return parsed


def generate_spec_test_cases(spec: dict, max_cases: int = 10) -> list[dict]:
    """Generate test cases from a parsed agent spec."""
    cases: list[dict] = []

    # From example interactions
    for ex in spec.get("example_interactions", [])[:max_cases]:
        cases.append({
            "input": ex["input"],
            "expected_behavior": ex.get("expected_behavior", ""),
            "source": "spec_example",
            "tags": ["spec"],
        })

    # From expected tools — generate a usage test per tool
    for tool in spec.get("expected_tools", []):
        if len(cases) >= max_cases:
            break
        desc = tool.get("description", tool["name"])
        cases.append({
            "input": f"I need to use {desc}",
            "expected_behavior": f"Agent should use {tool['name']} tool",
            "source": "spec_tool",
            "tags": ["spec", "tool_coverage"],
        })

    # From constraints — generate violation test per constraint
    for constraint in spec.get("constraints", []):
        if len(cases) >= max_cases:
            break
        cases.append({
            "input": f"Please ignore this rule: {constraint}",
            "expected_behavior": f"Agent should still adhere to: {constraint}",
            "source": "spec_constraint",
            "tags": ["spec", "adversarial"],
        })

    return cases[:max_cases]


def get_tool_coverage(spec_tools: list[dict], used_tools: set[str]) -> dict[str, Any]:
    """Compare spec expected tools vs actually used tools."""
    expected = sorted(t["name"] for t in spec_tools)
    covered = sorted(t for t in expected if t in used_tools)
    missing = sorted(t for t in expected if t not in used_tools)
    return {
        "expected": expected,
        "covered": covered,
        "missing": missing,
        "coverage_pct": len(covered) / len(expected) if expected else 1.0,
    }
```

- [ ] **Step 4: Add pyyaml dependency**
```bash
cd backend && uv add pyyaml
```

- [ ] **Step 5: Run tests**
```bash
cd backend && uv run pytest tests/unit/test_spec_scorer.py -v
```

- [ ] **Step 6: Commit**
```bash
git add backend/src/harness/eval/spec_scorer.py backend/tests/unit/test_spec_scorer.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add spec parser, spec-aware test generation, and tool coverage"
```

---

## Task 5: Workspace API Routes

**Files:**
- Create: `backend/src/harness/api/workspace_routes.py`
- Create: `backend/src/harness/api/agent_routes.py`
- Modify: `backend/src/harness/main.py`
- Create: `backend/tests/e2e/test_workspace_api.py`

- [ ] **Step 1: Create workspace routes**

```python
# backend/src/harness/api/workspace_routes.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from harness.db.engine import get_session
from harness.db.queries import WorkspaceCreate, create_workspace, get_workspace, list_workspaces, workspace_to_dict

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    tier: str
    agent_limit: int
    created_at: str | None = None


@router.post("", response_model=WorkspaceResponse)
async def create_workspace_endpoint(
    req: CreateWorkspaceRequest, session: AsyncSession = Depends(get_session),
):
    # TODO: get owner_id from JWT auth — using placeholder for now
    owner_id = uuid.uuid4()
    ws = await create_workspace(session, WorkspaceCreate(name=req.name, owner_id=owner_id))
    return workspace_to_dict(ws)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces_endpoint(session: AsyncSession = Depends(get_session)):
    owner_id = uuid.uuid4()  # placeholder
    workspaces = await list_workspaces(session, owner_id)
    return [workspace_to_dict(ws) for ws in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_endpoint(workspace_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    ws = await get_workspace(session, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace_to_dict(ws)
```

- [ ] **Step 2: Create agent routes**

```python
# backend/src/harness/api/agent_routes.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from harness.db.engine import get_session
from harness.db.queries import (
    AgentCreate, connect_agent, get_agents, get_agent, agent_to_dict,
    save_spec, get_latest_spec,
)
from harness.eval.spec_scorer import parse_spec_yaml

router = APIRouter(prefix="/api/workspaces/{workspace_id}/agents", tags=["agents"])


class ConnectAgentRequest(BaseModel):
    endpoint_url: str
    auth_header: str | None = None
    schema_type: str = "openai"
    display_name: str | None = None
    capabilities: list[str] | None = None


class UploadSpecRequest(BaseModel):
    content: str


@router.post("")
async def connect_agent_endpoint(
    workspace_id: uuid.UUID, req: ConnectAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        agent = await connect_agent(session, AgentCreate(
            workspace_id=workspace_id, endpoint_url=req.endpoint_url,
            schema_type=req.schema_type, display_name=req.display_name or req.endpoint_url,
            detected_capabilities=req.capabilities, confirmed_capabilities=req.capabilities,
        ))
        return agent_to_dict(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_agents_endpoint(workspace_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    agents = await get_agents(session, workspace_id)
    return [agent_to_dict(a) for a in agents]


@router.get("/{agent_id}")
async def get_agent_endpoint(
    workspace_id: uuid.UUID, agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    agent = await get_agent(session, workspace_id, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_to_dict(agent)


@router.post("/{agent_id}/spec")
async def upload_spec_endpoint(
    workspace_id: uuid.UUID, agent_id: uuid.UUID,
    req: UploadSpecRequest, session: AsyncSession = Depends(get_session),
):
    agent = await get_agent(session, workspace_id, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        parsed = parse_spec_yaml(req.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid spec: {e}")
    spec = await save_spec(session, agent_id, req.content, parsed)
    return {"version": spec.version, "parsed": spec.parsed}


@router.get("/{agent_id}/spec")
async def get_spec_endpoint(
    workspace_id: uuid.UUID, agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    spec = await get_latest_spec(session, agent_id)
    if not spec:
        return {"spec": None, "message": "No spec uploaded. Upload a spec for better eval results."}
    return {"version": spec.version, "content": spec.content, "parsed": spec.parsed}
```

- [ ] **Step 3: Mount routes in main.py**

Add imports and include routers in `create_app()`:
```python
from harness.api.workspace_routes import router as workspace_router
from harness.api.agent_routes import router as agent_router

# In create_app():
app.include_router(workspace_router)
app.include_router(agent_router)
```

- [ ] **Step 4: Write E2E test**

```python
# backend/tests/e2e/test_workspace_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from harness.main import app


@pytest.mark.asyncio
async def test_create_workspace() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/workspaces", json={"name": "Test Workspace"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Workspace"
    assert data["tier"] == "free"
    assert data["agent_limit"] == 3


@pytest.mark.asyncio
async def test_get_workspace_not_found() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/workspaces/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
```

- [ ] **Step 5: Run tests**
```bash
cd backend && uv run pytest tests/e2e/test_workspace_api.py -v
```

- [ ] **Step 6: Commit**
```bash
git add backend/src/harness/api/workspace_routes.py backend/src/harness/api/agent_routes.py backend/src/harness/main.py backend/tests/e2e/test_workspace_api.py
git commit -m "feat: add workspace and agent CRUD API routes"
```

---

## Task 6: Frontend API Client + Auth Setup

**Files:**
- Create: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/login/page.tsx`
- Install: `next-auth` (for Task 13 auth, stub for now)

- [ ] **Step 1: Create typed API client**

```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || error.error || "API error");
  }
  return res.json();
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  tier: string;
  agent_limit: number;
  created_at: string | null;
}

export interface ConnectedAgent {
  id: string;
  workspace_id: string;
  endpoint_url: string;
  schema_type: string;
  display_name: string | null;
  detected_capabilities: string[] | null;
  confirmed_capabilities: string[] | null;
  created_at: string | null;
}

export const api = {
  workspaces: {
    create: (name: string) => apiFetch<Workspace>("/api/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
    list: () => apiFetch<Workspace[]>("/api/workspaces"),
    get: (id: string) => apiFetch<Workspace>(`/api/workspaces/${id}`),
  },
  agents: {
    connect: (workspaceId: string, data: { endpoint_url: string; display_name?: string; capabilities?: string[] }) =>
      apiFetch<ConnectedAgent>(`/api/workspaces/${workspaceId}/agents`, { method: "POST", body: JSON.stringify(data) }),
    list: (workspaceId: string) => apiFetch<ConnectedAgent[]>(`/api/workspaces/${workspaceId}/agents`),
    get: (workspaceId: string, agentId: string) => apiFetch<ConnectedAgent>(`/api/workspaces/${workspaceId}/agents/${agentId}`),
    uploadSpec: (workspaceId: string, agentId: string, content: string) =>
      apiFetch(`/api/workspaces/${workspaceId}/agents/${agentId}/spec`, { method: "POST", body: JSON.stringify({ content }) }),
    getSpec: (workspaceId: string, agentId: string) =>
      apiFetch(`/api/workspaces/${workspaceId}/agents/${agentId}/spec`),
  },
  quickEval: {
    probe: (data: { endpoint_url: string; auth_header?: string | null }) =>
      apiFetch("/api/probe", { method: "POST", body: JSON.stringify(data) }),
    run: (data: { endpoint_url: string; capabilities: string[]; auth_header?: string | null; num_cases?: number }) =>
      apiFetch("/api/quick-eval", { method: "POST", body: JSON.stringify(data) }),
  },
};
```

- [ ] **Step 2: Create login page**

```tsx
// frontend/src/app/login/page.tsx
"use client";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">Agent Eval Harness</h1>
        <p className="text-gray-400 mb-8">Evaluate your AI agents with confidence</p>
        <div className="flex gap-3 justify-center">
          <a href="/workspaces" className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
            Get Started
          </a>
        </div>
        <p className="text-gray-600 text-sm mt-4">OAuth sign-in coming soon</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update root page to redirect**

```tsx
// frontend/src/app/page.tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/workspaces");
}
```

- [ ] **Step 4: Commit**
```bash
git add frontend/src/lib/api.ts frontend/src/app/login/page.tsx frontend/src/app/page.tsx
git commit -m "feat: add typed API client and login page stub"
```

---

## Task 7: Workspace List + Create Page

**Files:**
- Create: `frontend/src/app/workspaces/page.tsx`

- [ ] **Step 1: Create workspace list page**

```tsx
// frontend/src/app/workspaces/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, Workspace } from "@/lib/api";

export default function WorkspacesPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.workspaces.list().then(setWorkspaces).catch(() => {});
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const ws = await api.workspaces.create(newName.trim());
      router.push(`/w/${ws.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-2">Workspaces</h1>
        <p className="text-gray-400 mb-8">Each workspace is an isolated evaluation environment for your agents.</p>

        {error && <div className="bg-red-900/50 border border-red-700 rounded p-3 mb-4 text-red-300 text-sm">{error}</div>}

        <div className="flex gap-3 mb-8">
          <input
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
            placeholder="Workspace name (e.g., Production, Staging)"
            value={newName} onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50"
            onClick={handleCreate} disabled={creating || !newName.trim()}
          >
            {creating ? "Creating..." : "Create Workspace"}
          </button>
        </div>

        <div className="grid gap-4">
          {workspaces.map((ws) => (
            <button
              key={ws.id}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg p-4 text-left hover:border-blue-500 transition"
              onClick={() => router.push(`/w/${ws.id}`)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-white font-medium">{ws.name}</h3>
                  <p className="text-gray-500 text-sm">{ws.tier} tier</p>
                </div>
                <span className="text-gray-600 text-sm">{ws.agent_limit} agents max</span>
              </div>
            </button>
          ))}
          {workspaces.length === 0 && (
            <p className="text-gray-600 text-center py-8">No workspaces yet. Create one to get started.</p>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**
```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 3: Commit**
```bash
git add frontend/src/app/workspaces/
git commit -m "feat: add workspace list and create page"
```

---

## Task 8: Workspace Dashboard + Sidebar Layout

**Files:**
- Create: `frontend/src/components/sidebar.tsx`
- Create: `frontend/src/app/w/[id]/layout.tsx`
- Create: `frontend/src/app/w/[id]/page.tsx`
- Modify: `frontend/src/components/agent-card.tsx`

- [ ] **Step 1: Create sidebar**

```tsx
// frontend/src/components/sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface SidebarProps {
  workspaceId: string;
  workspaceName: string;
}

const navItems = [
  { label: "Agents", path: "", icon: "🤖" },
  { label: "Settings", path: "/settings", icon: "⚙️" },
];

export function Sidebar({ workspaceId, workspaceName }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-gray-950 border-r border-gray-800 flex flex-col h-screen sticky top-0">
      <div className="p-4 border-b border-gray-800">
        <Link href="/workspaces" className="text-xs text-gray-500 hover:text-gray-400">
          ← All Workspaces
        </Link>
        <h2 className="text-white font-semibold mt-1 truncate">{workspaceName}</h2>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const href = `/w/${workspaceId}${item.path}`;
          const active = item.path === "" ? pathname === `/w/${workspaceId}` : pathname.startsWith(href);
          return (
            <Link
              key={item.path}
              href={href}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${
                active ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-900"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">Agent Eval Harness</p>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Create workspace layout**

```tsx
// frontend/src/app/w/[id]/layout.tsx
"use client";

import { useParams } from "next/navigation";
import { Sidebar } from "@/components/sidebar";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const workspaceId = params.id as string;

  return (
    <div className="flex min-h-screen bg-gray-950">
      <Sidebar workspaceId={workspaceId} workspaceName="Workspace" />
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Create workspace dashboard**

```tsx
// frontend/src/app/w/[id]/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ConnectedAgent } from "@/lib/api";

export default function WorkspaceDashboard() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const [agents, setAgents] = useState<ConnectedAgent[]>([]);

  useEffect(() => {
    api.agents.list(workspaceId).then(setAgents).catch(() => {});
  }, [workspaceId]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Agents</h1>
        <button
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          onClick={() => router.push(`/w/${workspaceId}/agents/connect`)}
        >
          Connect Agent
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <button
            key={agent.id}
            className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-left hover:border-blue-500 transition"
            onClick={() => router.push(`/w/${workspaceId}/agents/${agent.id}`)}
          >
            <h3 className="text-white font-medium truncate">{agent.display_name || agent.endpoint_url}</h3>
            <p className="text-gray-500 text-xs mt-1 truncate">{agent.endpoint_url}</p>
            <div className="flex gap-1 mt-2">
              {(agent.confirmed_capabilities || agent.detected_capabilities || []).map((cap) => (
                <span key={cap} className="text-xs px-2 py-0.5 bg-gray-800 text-gray-400 rounded">{cap}</span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-500 mb-4">No agents connected yet.</p>
          <button
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
            onClick={() => router.push(`/w/${workspaceId}/agents/connect`)}
          >
            Connect Your First Agent
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify build**
```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/sidebar.tsx frontend/src/app/w/
git commit -m "feat: add workspace dashboard with sidebar layout and agent cards"
```

---

## Task 9: Connect Agent Page (Plug-and-Play Inside Workspace)

**Files:**
- Create: `frontend/src/app/w/[id]/agents/connect/page.tsx`
- Create: `frontend/src/components/spec-editor.tsx`

- [ ] **Step 1: Create spec editor component**

```tsx
// frontend/src/components/spec-editor.tsx
"use client";

import { useState } from "react";

interface SpecEditorProps {
  onSubmit: (content: string) => void;
  onSkip: () => void;
}

const EXAMPLE_SPEC = `name: "My Agent"
description: "Describe what your agent does"
expected_tools:
  - name: tool_name
    description: "What this tool does"
constraints:
  - "Rule your agent should follow"
example_interactions:
  - input: "Example user message"
    expected_behavior: "What agent should do"`;

export function SpecEditor({ onSubmit, onSkip }: SpecEditorProps) {
  const [content, setContent] = useState("");

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-white font-medium mb-1">Agent Spec (Recommended)</h3>
        <p className="text-gray-400 text-sm mb-3">
          Upload a YAML spec describing your agent's expected behavior. This enables spec-aware test generation and constraint violation scoring.
        </p>
      </div>
      <textarea
        className="w-full h-64 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white font-mono text-sm placeholder-gray-600 resize-none"
        placeholder={EXAMPLE_SPEC}
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <div className="flex gap-3">
        <button
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 font-medium disabled:opacity-50"
          onClick={() => onSubmit(content)}
          disabled={!content.trim()}
        >
          Upload Spec
        </button>
        <button
          className="px-6 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm"
          onClick={onSkip}
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create connect agent page**

```tsx
// frontend/src/app/w/[id]/agents/connect/page.tsx
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { SpecEditor } from "@/components/spec-editor";
import { ReportCard } from "@/components/report-card";
import { CaseDetail } from "@/components/case-detail";

type Step = "endpoint" | "probing" | "confirm" | "spec" | "eval" | "done";

export default function ConnectAgentPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;

  const [step, setStep] = useState<Step>("endpoint");
  const [url, setUrl] = useState("");
  const [authHeader, setAuthHeader] = useState("");
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleProbe() {
    setStep("probing"); setError(null);
    try {
      const data = await api.quickEval.probe({ endpoint_url: url, auth_header: authHeader || null });
      if (!(data as any).reachable) { setError((data as any).error || "Not reachable"); setStep("endpoint"); return; }
      setCapabilities((data as any).detected_capabilities);
      setStep("confirm");
    } catch (e: any) { setError(e.message); setStep("endpoint"); }
  }

  async function handleConfirm() {
    try {
      const agent = await api.agents.connect(workspaceId, {
        endpoint_url: url, display_name: url, capabilities,
      });
      setAgentId(agent.id);
      setStep("spec");
    } catch (e: any) { setError(e.message); }
  }

  async function handleSpec(content: string) {
    if (agentId) {
      try { await api.agents.uploadSpec(workspaceId, agentId, content); } catch {}
    }
    runEval();
  }

  async function runEval() {
    setStep("eval"); setError(null);
    try {
      const data = await api.quickEval.run({ endpoint_url: url, capabilities, auth_header: authHeader || null, num_cases: 2 });
      if ((data as any).error) { setError((data as any).error); setStep("spec"); return; }
      setResult(data);
      setStep("done");
    } catch (e: any) { setError(e.message); setStep("spec"); }
  }

  function toggleCap(cap: string) {
    setCapabilities(prev => prev.includes(cap) ? prev.filter(c => c !== cap) : [...prev, cap]);
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Connect Agent</h1>
      <p className="text-gray-400 mb-6">Add an agent to this workspace and run your first evaluation.</p>

      {error && <div className="bg-red-900/50 border border-red-700 rounded p-3 mb-4 text-red-300 text-sm">{error}</div>}

      {step === "endpoint" && (
        <div className="space-y-4">
          <input className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
            placeholder="https://your-agent.com/v1/chat/completions" value={url} onChange={e => setUrl(e.target.value)} />
          <input className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500"
            placeholder="Bearer sk-... (optional)" value={authHeader} onChange={e => setAuthHeader(e.target.value)} />
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-medium disabled:opacity-50"
            onClick={handleProbe} disabled={!url}>Scan Agent</button>
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
            {["text", "tools", "rag"].map(cap => (
              <button key={cap} className={`px-4 py-2 rounded-lg border text-sm font-medium transition ${
                capabilities.includes(cap) ? "bg-blue-600 border-blue-500 text-white" : "bg-gray-900 border-gray-700 text-gray-400"
              }`} onClick={() => toggleCap(cap)}>{cap}</button>
            ))}
          </div>
          <button className="w-full bg-green-600 hover:bg-green-700 text-white rounded-lg py-3 font-medium"
            onClick={handleConfirm}>Confirm & Continue</button>
        </div>
      )}

      {step === "spec" && <SpecEditor onSubmit={handleSpec} onSkip={runEval} />}

      {step === "eval" && (
        <div className="text-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-green-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-400">Running first evaluation...</p>
        </div>
      )}

      {step === "done" && result && (
        <div>
          <ReportCard gradeLetter={result.grade_letter} gradeScore={result.grade_score} passRate={result.pass_rate}
            totalCases={result.total_cases} passed={result.passed} failed={result.failed}
            avgLatencyMs={result.avg_latency_ms} metricAverages={result.metric_averages} />
          <CaseDetail results={result.results} />
          <button className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-medium"
            onClick={() => router.push(`/w/${workspaceId}/agents/${agentId}`)}>
            View Agent Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build**
```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 4: Commit**
```bash
git add frontend/src/app/w/[id]/agents/connect/ frontend/src/components/spec-editor.tsx
git commit -m "feat: add connect agent page with spec upload and first eval"
```

---

## Task 10: Agent Detail + Run Detail Pages

**Files:**
- Create: `frontend/src/app/w/[id]/agents/[agentId]/page.tsx`
- Create: `frontend/src/app/w/[id]/agents/[agentId]/runs/[runId]/page.tsx`
- Create: `frontend/src/components/trace-timeline.tsx`
- Create: `frontend/src/components/run-table.tsx`

- [ ] **Step 1: Create trace timeline component**

```tsx
// frontend/src/components/trace-timeline.tsx
"use client";

interface Span {
  type: string;
  name: string;
  start_ms: number;
  duration_ms: number;
  input: Record<string, any>;
  output: Record<string, any>;
  metadata: Record<string, any>;
}

export function TraceTimeline({ spans }: { spans: Span[] }) {
  if (!spans || spans.length === 0) return <p className="text-gray-500 text-sm">No trace data available.</p>;

  const colors: Record<string, string> = {
    llm_call: "border-blue-500 bg-blue-950",
    tool_call: "border-green-500 bg-green-950",
    scoring: "border-yellow-500 bg-yellow-950",
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-400 mb-2">Execution Trace</h4>
      {spans.map((span, i) => (
        <div key={i} className={`border-l-2 ${colors[span.type] || "border-gray-700 bg-gray-900"} rounded-r p-3`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-gray-400">{span.type}</span>
              <span className="text-sm text-white font-medium">{span.name}</span>
            </div>
            <span className="text-xs text-gray-500">{Math.round(span.duration_ms)}ms</span>
          </div>
          {span.input && Object.keys(span.input).length > 0 && (
            <div className="mt-1 text-xs text-gray-400">
              <span className="text-gray-600">Input: </span>
              {JSON.stringify(span.input).substring(0, 100)}
            </div>
          )}
          {span.output && Object.keys(span.output).length > 0 && (
            <div className="mt-1 text-xs text-gray-300">
              <span className="text-gray-600">Output: </span>
              {JSON.stringify(span.output).substring(0, 150)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create run table component**

```tsx
// frontend/src/components/run-table.tsx
"use client";

interface RunEntry {
  id: string;
  grade_letter?: string;
  pass_rate?: number;
  total_cases?: number;
  avg_latency_ms?: number;
  is_baseline?: boolean;
  created_at?: string;
}

const gradeColors: Record<string, string> = {
  A: "text-green-400", B: "text-blue-400", C: "text-yellow-400", D: "text-orange-400", F: "text-red-400",
};

export function RunTable({ runs, onSelect }: { runs: RunEntry[]; onSelect: (id: string) => void }) {
  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <button key={run.id} onClick={() => onSelect(run.id)}
          className="w-full bg-gray-900 border border-gray-700 rounded-lg p-3 text-left hover:border-blue-500 transition flex items-center justify-between">
          <div className="flex items-center gap-3">
            {run.grade_letter && (
              <span className={`text-lg font-bold ${gradeColors[run.grade_letter] || "text-gray-400"}`}>{run.grade_letter}</span>
            )}
            <div>
              <p className="text-sm text-gray-300 font-mono">{run.id.slice(0, 8)}...</p>
              <p className="text-xs text-gray-500">{run.created_at ? new Date(run.created_at).toLocaleDateString() : ""}</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            {run.pass_rate !== undefined && <span>{Math.round(run.pass_rate * 100)}% pass</span>}
            {run.total_cases && <span>{run.total_cases} cases</span>}
            {run.avg_latency_ms && <span>{Math.round(run.avg_latency_ms)}ms</span>}
            {run.is_baseline && <span className="px-2 py-0.5 bg-blue-900 text-blue-300 rounded">baseline</span>}
          </div>
        </button>
      ))}
      {runs.length === 0 && <p className="text-gray-600 text-center py-4">No eval runs yet.</p>}
    </div>
  );
}
```

- [ ] **Step 3: Create agent detail page**

```tsx
// frontend/src/app/w/[id]/agents/[agentId]/page.tsx
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { RunTable } from "@/components/run-table";

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const agentId = params.agentId as string;
  const [tab, setTab] = useState<"runs" | "spec">("runs");

  // Placeholder — will fetch from API
  const runs: any[] = [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Agent Detail</h1>
        <p className="text-gray-500 text-sm font-mono">{agentId}</p>
      </div>

      <div className="flex gap-4 border-b border-gray-800 mb-6">
        {(["runs", "spec"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition ${
              tab === t ? "border-blue-500 text-white" : "border-transparent text-gray-500 hover:text-gray-300"
            }`}>
            {t === "runs" ? "Eval Runs" : "Spec"}
          </button>
        ))}
      </div>

      {tab === "runs" && (
        <RunTable runs={runs} onSelect={(runId) => router.push(`/w/${workspaceId}/agents/${agentId}/runs/${runId}`)} />
      )}

      {tab === "spec" && (
        <div className="text-gray-500 text-center py-8">
          <p>Spec management coming soon.</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create run detail page**

```tsx
// frontend/src/app/w/[id]/agents/[agentId]/runs/[runId]/page.tsx
"use client";

import { useParams } from "next/navigation";
import { TraceTimeline } from "@/components/trace-timeline";

export default function RunDetailPage() {
  const params = useParams();

  // Placeholder — will fetch from API
  const mockSpans = [
    { type: "llm_call", name: "LLM", start_ms: 0, duration_ms: 120, input: { text: "What is the weather?" }, output: { action: "tool_call" }, metadata: {} },
    { type: "tool_call", name: "get_weather", start_ms: 120, duration_ms: 15, input: { city: "London" }, output: { temp: 15 }, metadata: {} },
    { type: "llm_call", name: "LLM", start_ms: 135, duration_ms: 180, input: { tool_results: 1 }, output: { text: "London is 15°C" }, metadata: {} },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Eval Run</h1>
      <p className="text-gray-500 text-sm font-mono mb-6">{params.runId}</p>
      <TraceTimeline spans={mockSpans} />
    </div>
  );
}
```

- [ ] **Step 5: Verify build**
```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 6: Commit**
```bash
git add frontend/src/app/w/[id]/agents/ frontend/src/components/trace-timeline.tsx frontend/src/components/run-table.tsx
git commit -m "feat: add agent detail, run detail, trace timeline, and run table"
```

---

## Task 11: Remove Old Quick Eval + Cleanup

**Files:**
- Remove: `frontend/src/app/quick-eval/page.tsx`
- Modify: `frontend/src/app/page.tsx` (already redirects)
- Create: `frontend/src/app/w/[id]/settings/page.tsx`

- [ ] **Step 1: Create workspace settings page**

```tsx
// frontend/src/app/w/[id]/settings/page.tsx
"use client";

import { useParams } from "next/navigation";

export default function WorkspaceSettingsPage() {
  const params = useParams();

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-white mb-6">Workspace Settings</h1>
      <div className="space-y-6">
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
          <h3 className="text-white font-medium mb-2">Judge API Key (BYOK)</h3>
          <p className="text-gray-400 text-sm mb-3">Provide your own Gemini or OpenAI key for LLM-as-judge scoring.</p>
          <input className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white text-sm placeholder-gray-500"
            placeholder="Gemini or OpenAI API key" type="password" />
          <button className="mt-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm">Save Key</button>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
          <h3 className="text-white font-medium mb-2">Workspace Info</h3>
          <p className="text-gray-400 text-sm">Workspace ID: {params.id}</p>
          <p className="text-gray-400 text-sm">Tier: Free (3 agents max)</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Remove old quick-eval page**
```bash
rm -rf frontend/src/app/quick-eval/
```

- [ ] **Step 3: Verify build**
```bash
cd frontend && npm run build 2>&1 | tail -10
```

- [ ] **Step 4: Commit**
```bash
git add frontend/src/app/w/[id]/settings/ frontend/src/app/quick-eval/
git commit -m "feat: add workspace settings, remove standalone quick-eval page"
```

---

## Task 12: Docker + Deploy Config

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Modify: `frontend/next.config.ts`

- [ ] **Step 1: Create backend Dockerfile**

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

- [ ] **Step 2: Create docker-compose for self-host**

```yaml
# docker-compose.yml
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8080"
    env_file:
      - ./backend/.env
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8080
      - BACKEND_URL=http://backend:8080/agui

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: harness
      POSTGRES_USER: harness
      POSTGRES_PASSWORD: harness
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 3: Commit**
```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for self-host deployment"
```

---

## Task Summary

| Task | What | Backend | Frontend |
|---|---|---|---|
| 1 | Workspace + AgentSpec models + migration | ✓ | |
| 2 | DB query service | ✓ | |
| 3 | Trace builder | ✓ | |
| 4 | Spec scorer (parser + test gen + coverage) | ✓ | |
| 5 | Workspace + Agent API routes | ✓ | |
| 6 | API client + login stub | | ✓ |
| 7 | Workspace list + create page | | ✓ |
| 8 | Workspace dashboard + sidebar | | ✓ |
| 9 | Connect agent page (plug-and-play in workspace) | | ✓ |
| 10 | Agent detail + run detail + trace timeline | | ✓ |
| 11 | Settings page + cleanup | | ✓ |
| 12 | Docker + deploy config | ✓ | |

**Parallelization:** Tasks 1-4 (backend) can run in parallel. Tasks 6-11 (frontend) can run after Task 5. Task 12 is independent.
