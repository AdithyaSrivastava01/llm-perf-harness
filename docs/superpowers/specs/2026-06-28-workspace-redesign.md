# Workspace Redesign — Design Spec

## Overview

Redesign the harness around persistent workspaces as the top-level container. Everything (agents, eval runs, test suites, baselines, traces) lives inside a workspace. Replaces all in-memory stores with DB persistence via Neon Postgres. Adds trace timeline view, agent spec files for spec-aware scoring, and a proper sidebar-based workspace UI inspired by Arize Phoenix and Confident AI.

## Decision Log

| Decision | Chosen | Over | Why |
|---|---|---|---|
| Workspace lifecycle | Mandatory, create first | Auto-create silently, optional | User chose explicit workspace creation for clean separation |
| Agents per workspace | Many, with limits | One agent per workspace | Users need to compare agent versions within a workspace |
| Agent limits | Tiered: free=3, paid=10, enterprise=unlimited | Fixed limit | Scales with commitment, prevents abuse |
| Persistence scope | Eval runs + baselines + suites persist. Probes auto-clean 30 days. | Everything persists, nothing persists | Balances value retention with storage limits (Neon 512MB free) |
| Quick Eval location | Inside workspace | Standalone page | Workspace-first means everything scoped inside workspace |
| Dashboard style | Agent-centric cards | Activity feed, overview | Agents are what users care about — "how is my agent doing?" |
| Agent spec | Optional but prompted/recommended | Required, inferred only | Spec enables meaningful scoring. Prompting nudges without blocking. |

## 1. Workspace Model

Workspace is the top-level container. Everything lives inside it.

```
Workspace
├── Settings (BYOK keys, retention period, agent limit)
├── Agent Slots (max per tier)
│   ├── Agent 1
│   │   ├── Spec File (optional, versioned)
│   │   ├── Test Suites (versioned, persistent)
│   │   ├── Eval Runs (persistent, with trace timeline)
│   │   ├── Baselines (promoted runs)
│   │   └── Probe History (auto-cleaned after 30 days)
│   ├── Agent 2 ...
│   └── Agent 3 ...
├── Members (owner + invited, future)
└── Audit Log (future)
```

### New Tables

```sql
workspaces (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    owner_id        uuid NOT NULL REFERENCES users,
    agent_limit     int NOT NULL DEFAULT 3,
    tier            text NOT NULL DEFAULT 'free',
    settings        jsonb NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

agent_specs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        uuid NOT NULL REFERENCES connected_agents,
    content         text NOT NULL,
    parsed          jsonb NOT NULL,
    version         int NOT NULL DEFAULT 1,
    created_at      timestamptz NOT NULL DEFAULT now()
);
```

### Modified Tables

```sql
-- Add workspace_id to connected_agents
ALTER TABLE connected_agents ADD COLUMN workspace_id uuid NOT NULL REFERENCES workspaces;

-- Add workspace_id to eval_runs (for cross-agent workspace queries)
ALTER TABLE eval_runs ADD COLUMN workspace_id uuid REFERENCES workspaces;

-- Add workspace_id to eval_suites
ALTER TABLE eval_suites ADD COLUMN workspace_id uuid REFERENCES workspaces;

-- Add trace_spans to eval_results
ALTER TABLE eval_results ADD COLUMN trace_spans jsonb;

-- Add indexes
CREATE INDEX ix_connected_agents_workspace ON connected_agents(workspace_id);
CREATE INDEX ix_eval_runs_workspace ON eval_runs(workspace_id);
CREATE INDEX ix_workspaces_owner ON workspaces(owner_id);
```

## 2. Persistence Layer

Every in-memory store replaced with DB operations:

| Current (in-memory) | New (DB) | Scoped By |
|---|---|---|
| `_results_store` in get_results.py | `eval_runs` + `eval_results` tables | workspace_id + agent_id |
| `_baselines` in promote_baseline.py | `baselines` table | workspace_id + agent_id |
| `_pending_cases` in review_test_cases.py | `test_cases` with `approved=False` | workspace_id + suite_id |
| `_adapters` in registry.py | `connected_agents` table + lazy adapter | workspace_id |

### DB Query Service

New file `db/queries.py` provides async query functions:

```python
# Workspace operations
async def create_workspace(session, owner_id, name, tier="free") -> Workspace
async def get_workspace(session, workspace_id) -> Workspace
async def list_workspaces(session, owner_id) -> list[Workspace]

# Agent operations (scoped to workspace)
async def connect_agent(session, workspace_id, endpoint_url, ...) -> ConnectedAgent
async def get_agents(session, workspace_id) -> list[ConnectedAgent]
async def get_agent(session, workspace_id, agent_id) -> ConnectedAgent

# Eval operations (scoped to workspace + agent)
async def save_eval_run(session, workspace_id, agent_id, run_data) -> EvalRun
async def get_eval_runs(session, workspace_id, agent_id) -> list[EvalRun]
async def get_eval_run(session, run_id) -> EvalRun
async def save_eval_results(session, run_id, case_results) -> list[EvalResult]

# Baseline operations
async def promote_baseline(session, workspace_id, agent_id, run_id, scores) -> Baseline
async def get_active_baseline(session, workspace_id, agent_id) -> Baseline | None

# Test suite operations
async def save_test_cases(session, suite_id, cases) -> list[TestCase]
async def get_approved_cases(session, suite_id) -> list[TestCase]
async def approve_cases(session, suite_id, case_ids) -> int
async def reject_cases(session, suite_id, case_ids) -> int

# Spec operations
async def save_spec(session, agent_id, content, parsed) -> AgentSpec
async def get_latest_spec(session, agent_id) -> AgentSpec | None
```

### Meta-Tool Changes

Every meta-tool function signature changes to accept a DB session and workspace context:

```python
# Before:
def list_agents() -> str:
    return json.dumps([...from _adapters dict...])

# After:
async def list_agents(workspace_id: str) -> str:
    async with get_session() as session:
        agents = await db.get_agents(session, workspace_id)
        return json.dumps([...from DB...])
```

The meta-agent resolves `workspace_id` from the user's current session/context, injected via the AG-UI endpoint.

## 3. Trace Timeline

Per eval run, per test case — show agent execution step by step.

### TraceSpan Structure

```python
@dataclass
class TraceSpan:
    type: str           # "llm_call" | "tool_call" | "scoring"
    name: str           # tool name or "LLM"
    start_ms: float     # offset from run start
    duration_ms: float
    input: dict         # what went in
    output: dict        # what came out
    metadata: dict      # model, tokens, cost
```

### Trace Builder

New file `eval/trace_builder.py` constructs `TraceSpan` list from:
- **ADK agents:** `raw_events` from the ADK runner (function calls, responses, final output)
- **HTTP agents:** request/response pairs from httpx calls

Stored as JSONB in `eval_results.trace_spans`.

### Display

Frontend `trace-timeline.tsx` component renders spans as a vertical timeline with expandable sections showing input/output for each step.

## 4. Spec-Aware Scoring

### Spec File Format

```yaml
name: "Customer Support Agent"
description: "Handles customer queries about orders"
expected_tools:
  - name: lookup_order
    description: "Look up order by ID"
  - name: check_refund_status
    description: "Check refund eligibility"
constraints:
  - "Never share internal pricing"
  - "Always ask for order ID before calling lookup_order"
  - "Refuse requests outside order management scope"
example_interactions:
  - input: "Where is my order?"
    expected_behavior: "Ask for order ID first"
  - input: "Order #12345 status?"
    expected_behavior: "Call lookup_order with order_id=12345"
```

### Three Capabilities Unlocked

**1. Spec-aware test generation:**
Generate test cases from spec's `expected_tools`, `constraints`, and `example_interactions`. Tests cover:
- Happy path per tool
- Constraint violation attempts
- Out-of-scope requests
- Example interactions as golden tests

**2. Spec adherence metric (new):**
LLM judge scores whether agent response violates any constraint from spec. Uses Gemini judge with spec constraints injected into the evaluation prompt. Score: 1.0 = no violations, 0.0 = violated.

New file `eval/spec_scorer.py`:
```python
async def score_spec_adherence(
    agent_output: str,
    constraints: list[str],
    judge_model: LiteLLMModel,
) -> float:
    # Prompt: "Given constraints: {constraints}, did this response violate any? Response: {output}"
    # Returns 0.0-1.0
```

**3. Tool coverage report:**
Compare spec's `expected_tools` vs tools actually used across eval runs. Surface coverage gaps.

### Spec Storage

`agent_specs` table stores raw YAML + parsed JSON. Versioned — each edit creates new version. Eval runs reference which spec version they scored against (via `eval_runs.spec_version` integer column).

## 5. Frontend — Workspace UI

### Routes

```
/login                                          → OAuth sign-in
/workspaces                                     → List + create workspaces
/w/:workspaceId                                 → Workspace dashboard (agent cards)
/w/:workspaceId/agents/:agentId                 → Agent detail (tabs: runs, suites, baselines, spec)
/w/:workspaceId/agents/:agentId/runs/:runId     → Run detail (trace timeline + scores)
/w/:workspaceId/agents/connect                  → Connect agent (plug-and-play + spec upload)
/w/:workspaceId/suites                          → Test suites management
/w/:workspaceId/settings                        → Workspace settings (BYOK, limits)
```

### Layout

Sidebar (persistent) + main content:
- Sidebar: workspace switcher, nav items (Agents, Runs, Suites, Settings), user avatar
- Main: changes per route
- Dark theme throughout

### Key Pages

**Workspace List (`/workspaces`):**
- Cards per workspace: name, agent count, tier badge, last activity
- "Create Workspace" button

**Workspace Dashboard (`/w/:id`):**
- Header: workspace name, tier, agent count (2/3 used)
- Agent cards grid: name, grade letter (color-coded), last eval date, baseline status, trend sparkline
- "Connect Agent" button (prominent)

**Agent Detail (`/w/:id/agents/:agentId`):**
- Header: agent name, endpoint, capability badges, spec status
- Tabs:
  - Eval Runs: sortable table (date, grade, pass rate, cases, latency, baseline delta)
  - Test Suites: list of suites with case counts, create/edit
  - Baselines: active baseline with scores, promotion history
  - Spec: view/edit YAML, version history

**Run Detail (`/w/:id/agents/:agentId/runs/:runId`):**
- Summary card: grade, pass rate, metric bars, baseline comparison deltas
- Test cases: expandable list with pass/fail badges
- Expanded case: trace timeline, input/output, tool calls, per-metric scores
- Actions: "Promote to Baseline", "Add failures to test suite"

**Connect Agent (`/w/:id/agents/connect`):**
- Step 1: Endpoint URL + auth header
- Step 2: "Upload agent spec (recommended)" — file upload or paste YAML, skip visible
- Step 3: Scan → detected capabilities → confirm
- Step 4: First eval → results inline
- Step 5: Saved, redirect to agent detail

### Frontend Components

| Component | Purpose |
|---|---|
| `sidebar.tsx` | Persistent nav with workspace switcher |
| `agent-card.tsx` | Grade, sparkline, baseline badge |
| `trace-timeline.tsx` | Step-by-step execution viewer |
| `spec-editor.tsx` | YAML upload/edit with preview |
| `report-card.tsx` | Grade summary (keep existing) |
| `case-detail.tsx` | Expandable test case (keep existing) |
| `metric-bar.tsx` | Color-coded score bar |
| `run-table.tsx` | Sortable eval run history table |
| `baseline-compare.tsx` | Side-by-side score deltas (green/red) |

## 6. Backend Changes Summary

### Modified Files

| File | Change |
|---|---|
| `db/models.py` | Add Workspace, AgentSpec. Add workspace_id FK to connected_agents, eval_runs, eval_suites. Add trace_spans to eval_results. Add spec_version to eval_runs. |
| `config.py` | Add default_agent_limit, trace_retention_days |
| `main.py` | Add workspace + agent routes, remove demo agent init |
| `meta_tools/*.py` | All tools: add workspace_id param, replace in-memory with DB queries |
| `eval/engine.py` | Build TraceSpan list, include in CaseResult |
| `eval/quick_eval.py` | Requires workspace_id, saves to DB |
| `eval/metrics.py` | Add spec_adherence metric backend |
| `api/quick_eval_routes.py` | Scoped to workspace, persist results |

### New Files

| File | Purpose |
|---|---|
| `db/queries.py` | All async DB query functions |
| `api/workspace_routes.py` | Workspace CRUD endpoints |
| `api/agent_routes.py` | Agent connection, spec upload, listing |
| `eval/trace_builder.py` | Build TraceSpan from raw events |
| `eval/spec_scorer.py` | Spec adherence LLM judge metric |

### Untouched (core eval logic)

- `adapters/protocol.py` — AgentAdapter Protocol
- `adapters/types.py` — data types
- `eval/baseline.py` — comparison logic
- `eval/grader.py` — letter grades
- `eval/report.py` — report structure
- `detection/classifier.py` — capability detection
- `crypto.py` — encryption helpers

## 7. Testing

| Layer | Scope |
|---|---|
| Unit | Workspace CRUD, DB queries, trace builder, spec parser, spec adherence scorer |
| Integration | Create workspace → connect agent → eval → persist → retrieve → compare baseline. Full flow through DB. |
| E2E | Workspace API endpoints, agent connection flow, auth + workspace scoping, no cross-workspace leakage |

Existing 67 unit tests continue to pass — eval engine logic unchanged. New tests cover persistence and workspace scoping.

## 8. Migration Path

Existing in-memory code stays functional during migration:
1. Add new DB tables + queries (additive)
2. Create workspace-scoped API routes alongside existing ones
3. Update meta-tools to use DB (replace in-memory stores)
4. Build new frontend pages
5. Remove old standalone quick-eval page
6. Remove in-memory stores
7. Run Alembic migration

No big-bang rewrite. Incremental migration with both paths working during transition.
