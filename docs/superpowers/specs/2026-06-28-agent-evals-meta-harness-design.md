# Agent-Evals Meta-Harness — Design Spec

## Overview

A deployed web app where users interact with a conversational AI meta-agent to evaluate LLM agents. Ships with demo agents (tool-calling, RAG), auto-generates test cases, runs continuous evals with pluggable metrics, and surfaces results through a CopilotKit + AG-UI conversational interface. Built for real users (10-50 concurrent), with a path to BYOA (Bring Your Own Agent).

## Decision Log

| Decision | Chosen | Over | Why |
|---|---|---|---|
| Architecture | ADK meta-agent + pluggable eval backend | ADK-only, CopilotKit-first | Best eval coverage (ADK + DeepEval). Clean BYOA path. Uses each tool where strongest. |
| Frontend | CopilotKit + AG-UI conversational UI | Traditional dashboard | Product differentiator. No other eval tool has a conversational interface. AG-UI is production-ready with first-party ADK bridge. |
| Eval metrics | ADK (tool-trajectory, response match) + DeepEval (faithfulness, hallucination) | Single framework | ADK lacks RAG-specific metrics. DeepEval lacks tool-trajectory. Combined = full coverage for both demo agents. |
| Database | Neon serverless Postgres | Supabase, managed Postgres | Serverless pairs with Cloud Run scale-to-zero. No idle connection limits. Supabase auth helpers redundant since we use NextAuth. |
| Auth | NextAuth.js (Google + GitHub OAuth) | Custom OAuth, Supabase Auth | One config, two providers, JWT strategy fits serverless. Rolling custom OAuth wastes 3-4 days. |
| Backend hosting | Cloud Run scale-to-zero | Render, Railway, Fly.io | Free tier (180k vCPU-s/mo). One-command ADK deploy. Cold start ~1-3s acceptable for MVP. Others have weaker/expiring free tiers. |
| Frontend hosting | Vercel Hobby | Netlify, self-hosted | Native Next.js host. Edge CDN. Zero config. |
| ORM | SQLAlchemy async + asyncpg | Prisma, raw SQL | Matches Python backend. Battle-tested with Postgres. Alembic migrations. |
| Judge model | Gemini Flash (default) | GPT-4o, Claude | Cheapest per-token for eval judging (~$0.01/run). Model-agnostic via LiteLLM for flexibility. |
| Traces | Grafana Cloud Free (OTel) | Self-hosted Jaeger, Datadog | 50GB/mo free. No self-hosting. Good trace UI. OTel GenAI conventions = vendor-neutral. |

## 1. System Architecture

Three-layer split with strict boundaries:

### Conversational Layer
ADK meta-agent served via `ag_ui_adk` → CopilotKit frontend. User talks naturally, meta-agent orchestrates evals via tools.

### Eval Engine Layer
Framework-agnostic eval runner. Takes an `AgentAdapter` + `EvalSuite`, executes agent against test cases, scores with appropriate metric backend (ADK or DeepEval), stores results. Emits OTel spans.

### Agent Layer
Demo agents (tool-calling, RAG) as ADK agents. `AgentAdapter` Protocol wraps them for the eval engine. BYOA agents get their own adapter implementations later.

### Data Flow

```
User <-> CopilotKit (Next.js/Vercel) <-> AG-UI/SSE <-> FastAPI + ag_ui_adk (Cloud Run)
                                                            |
                                                      ADK Meta-Agent
                                                        (tools)
                                                            |
                                                  +-------------------+
                                                  |   Eval Engine     |
                                                  | +------+ +-----+ |
                                                  | | ADK  | |Deep | |
                                                  | |Metric| |Eval | |
                                                  | +------+ +-----+ |
                                                  +--------+----------+
                                                           |
                                                  +-------------------+
                                                  |  Agent Adapters   |
                                                  | +------+ +-----+ |
                                                  | |Tool  | |RAG  | |
                                                  | |Agent | |Agent| |
                                                  | +------+ +-----+ |
                                                  +-------------------+
                                                           |
                                                     Neon Postgres
                                              (results, sessions, users)
```

**Key boundary:** Eval Engine knows nothing about CopilotKit/AG-UI. Meta-agent knows nothing about scoring internals. Agents know nothing about how they're evaluated. Each layer testable independently.

## 2. Eval Engine Design

### EvalSuite

```python
class EvalSuite:
    name: str
    agent_adapter: AgentAdapter
    test_cases: list[TestCase]
    metrics: list[MetricConfig]   # which metrics + thresholds
    baseline: Baseline | None     # for regression detection
```

### TestCase

```python
class TestCase:
    id: str
    input: list[Turn]                       # conversation turns
    expected_tools: list[ToolCall] | None    # for tool-trajectory
    expected_output: str | None             # for response matching
    reference_contexts: list[str] | None    # for RAG faithfulness
    tags: list[str]                         # grouping/filtering
```

### Metric Routing

| Metric | Backend | Used For |
|---|---|---|
| `tool_trajectory_avg_score` | ADK | Tool-calling agent — right tools, right order |
| `response_match_score` | ADK | Basic response similarity (ROUGE-1) |
| `final_response_match_v2` | ADK | LLM-as-judge semantic equivalence |
| `faithfulness` | DeepEval | RAG — answer grounded in retrieved context |
| `contextual_relevancy` | DeepEval | RAG — retrieved relevant docs |
| `hallucination` | DeepEval | RAG — no fabricated information |
| `answer_relevancy` | DeepEval | Both — response answers the question |

### Unified Metric Result

```python
class MetricResult:
    name: str
    score: float           # 0.0 - 1.0 normalized
    passed: bool           # score >= threshold
    threshold: float
    details: dict          # backend-specific explanation
    backend: str           # "adk" | "deepeval"
```

### Eval Run Flow

1. Load `EvalSuite` -> iterate `TestCase`s
2. Per case: invoke agent via `AgentAdapter.invoke()` -> collect response + tool calls
3. Per case: route to configured metrics -> collect `MetricResult`s
4. Aggregate into `EvalReport` (pass/fail per case, per metric, overall)
5. Compare against `Baseline` if present -> flag regressions
6. Emit OTel spans for entire run
7. Store `EvalReport` in Neon

### Baseline / Regression Detection

- Baseline = JSON snapshot of metric scores from last "golden" run
- Flag regression if any metric drops below absolute floor OR drops > 5 percentage points vs baseline (configurable per metric)
- Baselines stored per agent per suite in Neon
- One active baseline per agent+suite pair
- Baselines only promoted via explicit user action (HITL)

## 3. Agent Adapter Protocol

```python
class AgentAdapter(Protocol):
    """Wraps any agent into something the eval engine can drive."""

    @property
    def agent_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def capabilities(self) -> set[str]: ...   # {"text", "tools", "rag"}

    async def invoke(
        self, input: list[Turn], context: RunContext
    ) -> AgentResponse: ...
    # Turn = {"role": "user"|"assistant", "content": str}
    # RunContext = {run_id, suite_id, timeout_s, model_override}

    def supported_metrics(self) -> list[str]: ...   # which metrics apply

    def expected_tools(self) -> list[ToolSpec] | None: ...   # for tool-trajectory

    def reference_contexts(self) -> list[str] | None: ...    # for RAG grounding
```

### AgentResponse

```python
class AgentResponse:
    output: str                         # final text response
    tool_calls: list[ToolCall]          # tools invoked during execution
    retrieved_contexts: list[str]       # docs retrieved (RAG agents)
    latency_ms: float                   # wall clock time
    token_usage: TokenUsage             # input/output/total tokens
    raw_events: list[Event]             # full ADK event stream for debugging
```

### MVP Adapters

**ToolCallingAdapter** — wraps ADK LlmAgent with tools (weather, calculator, search):
- `capabilities`: `{"text", "tools"}`
- `supported_metrics`: `["tool_trajectory_avg_score", "final_response_match_v2", "answer_relevancy"]`
- `expected_tools()`: returns tool specs for trajectory scoring
- `reference_contexts()`: `None`

**RAGAdapter** — wraps ADK LlmAgent with retrieval tool backed by a curated doc set (~50 documents, e.g., technical FAQ or product docs):
- `capabilities`: `{"text", "tools", "rag"}`
- `supported_metrics`: `["faithfulness", "contextual_relevancy", "hallucination", "answer_relevancy"]`
- `expected_tools()`: returns retriever tool spec
- `reference_contexts()`: returns source docs per query

### BYOA Path (Phase 2)

**HTTPAgentAdapter** — user provides endpoint URL + auth token. Adapter sends turns via HTTP, parses response into `AgentResponse`. User maps their response schema to ours via config. Metric selection based on declared capabilities.

## 4. Meta-Agent & Conversational UI

### Meta-Agent Tools

| Tool | What It Does |
|---|---|
| `list_agents` | Returns available demo agents + capabilities |
| `list_metrics` | Returns available metrics per agent type |
| `generate_test_cases` | Auto-generates test cases using ADK User Simulator |
| `review_test_cases` | Presents generated cases for user approval/editing |
| `run_eval` | Executes eval suite, streams progress |
| `get_results` | Fetches eval results with filtering |
| `compare_runs` | Diffs two eval runs, highlights regressions |
| `promote_baseline` | HITL — marks a run as golden baseline |
| `explain_failure` | Deep-dives a failing case — trace, docs, judge reasoning |

### CopilotKit Integration

```
Next.js (Vercel)
  +-- CopilotKit Provider
       +-- @ag-ui/client HttpAgent -> FastAPI endpoint
            +-- ag_ui_adk ADKAgent wrapper
                 +-- ADK LlmAgent (meta-agent)
                      +-- tools (above)
```

### UI Components (CopilotKit + shadcn/ui)

| Component | Purpose |
|---|---|
| Chat panel | Primary interaction — CopilotKit chat UI |
| Agent cards | Show available agents + capabilities |
| Test case list | Review/approve generated cases, inline edit |
| Results table | Per-case pass/fail, scores, expandable details |
| Run history | Past eval runs, trend sparklines |
| Trace viewer | Drill into agent event stream for specific case |

### Core UX Flow

1. User lands -> chat greets them, shows available demo agents
2. "Run eval on the tool-calling agent" -> meta-agent generates cases -> presents for review
3. User approves -> eval runs, progress streams live
4. Results appear in structured view -> user explores failures
5. "Explain why case 3 failed" -> meta-agent shows trace + judge reasoning
6. "This looks good, set as baseline" -> baseline locked

### Human-in-the-Loop (MVP)

**Baseline approval:** User explicitly promotes a run to golden baseline. No auto-promotion.

**Test case curation:** Auto-generated cases presented for review. User approves, edits, or removes before eval runs. Approved flag stored per test case.

**Deferred (Phase 2):** Live human grading mid-eval-run for uncertain LLM judge outputs.

## 5. Auth & Data Model

### Auth — NextAuth.js

- Google + GitHub OAuth providers
- JWT session strategy (stateless, fits serverless)
- JWT contains `user_id`, `email`, `name`, `provider`
- Frontend sends JWT in Authorization header to FastAPI
- FastAPI validates JWT on every request
- No roles/permissions for MVP

### Data Model (Neon Postgres)

```sql
-- Users
users (
    id          uuid PRIMARY KEY,
    email       text UNIQUE NOT NULL,
    name        text NOT NULL,
    auth_provider text NOT NULL,        -- "google" | "github"
    avatar_url  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);

-- Agents (demo + future BYOA)
agents (
    id          uuid PRIMARY KEY,
    name        text NOT NULL,
    description text,
    adapter_type text NOT NULL,          -- "tool_calling" | "rag" | "http"
    config      jsonb NOT NULL,          -- model, tools, system prompt, endpoint
    capabilities text[] NOT NULL,
    is_demo     boolean NOT NULL DEFAULT false,
    created_by  uuid REFERENCES users,   -- null for demo agents
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Eval Suites
eval_suites (
    id          uuid PRIMARY KEY,
    name        text NOT NULL,
    agent_id    uuid NOT NULL REFERENCES agents,
    created_by  uuid NOT NULL REFERENCES users,
    config      jsonb NOT NULL,          -- metrics, thresholds
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Test Cases
test_cases (
    id                  uuid PRIMARY KEY,
    suite_id            uuid NOT NULL REFERENCES eval_suites,
    input               jsonb NOT NULL,
    expected_output     text,
    expected_tools      jsonb,
    reference_contexts  jsonb,
    tags                text[],
    approved            boolean NOT NULL DEFAULT false,
    created_at          timestamptz NOT NULL DEFAULT now()
);

-- Eval Runs
eval_runs (
    id            uuid PRIMARY KEY,
    suite_id      uuid NOT NULL REFERENCES eval_suites,
    triggered_by  uuid NOT NULL REFERENCES users,
    status        text NOT NULL DEFAULT 'pending',
    started_at    timestamptz,
    completed_at  timestamptz,
    summary       jsonb,
    is_baseline   boolean NOT NULL DEFAULT false,
    otel_trace_id text
);

-- Eval Results (per test case per run)
eval_results (
    id              uuid PRIMARY KEY,
    run_id          uuid NOT NULL REFERENCES eval_runs,
    test_case_id    uuid NOT NULL REFERENCES test_cases,
    agent_response  jsonb NOT NULL,
    metric_results  jsonb NOT NULL,
    passed          boolean NOT NULL,
    latency_ms      float NOT NULL
);

-- Baselines
baselines (
    id          uuid PRIMARY KEY,
    agent_id    uuid NOT NULL REFERENCES agents,
    suite_id    uuid NOT NULL REFERENCES eval_suites,
    run_id      uuid NOT NULL REFERENCES eval_runs,
    scores      jsonb NOT NULL,
    promoted_by uuid NOT NULL REFERENCES users,
    promoted_at timestamptz NOT NULL DEFAULT now(),
    active      boolean NOT NULL DEFAULT true
);
```

### Indexes

- `eval_runs(suite_id, created_at)` — run history
- `eval_results(run_id)` — fetch results for a run
- `test_cases(suite_id, approved)` — load approved cases
- `baselines(agent_id, suite_id, active)` — find current baseline

## 6. Deployment Architecture

### Free Hosting Stack

| Component | Host | Free Tier |
|---|---|---|
| FastAPI backend | Cloud Run (scale-to-zero) | 180k vCPU-s + 360k GiB-s + 2M req/mo |
| Next.js frontend | Vercel Hobby | 100GB bandwidth, 1M invocations |
| Postgres | Neon Free | 512MB, autosuspend after 5min |
| OTel traces | Grafana Cloud Free | 50GB traces/mo, 14-day retention |
| Object storage | Cloud Storage | 5GB free |

**Total monthly cost: $0** for 10-50 intermittent users.

### Cold Start Mitigation (Free)

- Cloud Run: `min-instances=0`, `max-instances=4`, `cpu-boost=true`
- Neon: built-in pgbouncer connection pooling
- Vercel: edge caching for static assets

### Scaling Path (Post-Validation)

- Cloud Run `min-instances=1` (~$10/mo) to kill cold starts
- Neon Launch ($19/mo) for 10GB + more compute
- Upstash Redis (free tier) for eval job queue
- Modal for offloading heavy eval batches

### Environment Variables

```
# Backend (Cloud Run)
GOOGLE_API_KEY              # Gemini Flash
OPENAI_API_KEY              # Demo agents
DATABASE_URL                # Neon
OTEL_EXPORTER_OTLP_ENDPOINT # Grafana Cloud
JWT_SECRET                  # Validate frontend JWTs

# Frontend (Vercel)
NEXTAUTH_SECRET
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET
NEXT_PUBLIC_API_URL         # Cloud Run backend URL
```

## 7. Testing Strategy

### Test Layers

| Layer | Scope | Tool | Target Runtime |
|---|---|---|---|
| Unit | Metric routing, baseline comparison, adapter compliance, report aggregation | `pytest` + `pytest-asyncio`, mock LLM | Every commit, <30s |
| Integration | Agent -> eval -> results, DB CRUD, adapter wrapping real ADK agent | `pytest` + Gemini Flash, Neon branch DB | PR merge, <3min |
| E2E | FastAPI endpoints, ag_ui_adk SSE, OAuth flow | `pytest` + `httpx` async client | Pre-deploy, <2min |
| Manual | Full conversational flow, CopilotKit rendering, cross-browser | Human | Each milestone |

### Skipped (and Why)

- Frontend E2E (Playwright) — UI too volatile during MVP
- Load testing — 10-50 users won't stress serverless
- Snapshot tests — no stable UI yet
- Contract tests — single team, single repo

### Test Fixtures

- Deterministic mock agents (fixed responses, no LLM) for unit tests
- Gemini Flash for integration tests (~$0.01/run)
- Pre-built evalsets (5-10 cases) as JSON fixtures in repo

## 8. Phased Build Plan

### Week 1: Foundation + Eval Engine

- Days 1-2: Project scaffold (`uv init`, FastAPI, Neon DB, Alembic migrations, SQLAlchemy models)
- Days 3-4: `AgentAdapter` Protocol + `ToolCallingAdapter` with real ADK LlmAgent. Unit tests.
- Day 5: Eval engine core — `EvalSuite` runner, ADK metrics, `EvalReport`. Unit + integration tests.

**Milestone:** `pytest` runs eval suite against tool-calling agent, produces scored EvalReport.

### Week 2: RAG Agent + Meta-Agent + CopilotKit

- Days 1-2: `RAGAdapter` with retrieval tool. DeepEval metrics. Integration tests.
- Days 3-4: ADK meta-agent with tools. Serve via `ag_ui_adk` + FastAPI. Test SSE stream.
- Day 5: Next.js + CopilotKit scaffold on Vercel. Connect to backend. First conversational eval run end-to-end.

**Milestone:** Chat with meta-agent in browser, trigger eval, see results stream back.

### Week 3: Auth + HITL + Polish

- Day 1: NextAuth.js (Google + GitHub OAuth). JWT validation in FastAPI.
- Days 2-3: HITL flows — test case generation/review/approval, baseline promotion, regression detection.
- Days 4-5: UI polish — agent cards, results table, test case review, run history. CopilotKit + shadcn/ui.

**Milestone:** Authenticated users generate, review, run, compare, promote. Looks presentable.

### Week 4: Deploy + OTel + Harden

- Days 1-2: Cloud Run deploy (Dockerfile, scale-to-zero, cpu-boost). Vercel production. Neon production branch.
- Day 3: OTel instrumentation — spans per eval run/agent invocation. Grafana Cloud export.
- Day 4: Error handling, rate limiting, input validation (Zod + Pydantic). E2E tests.
- Day 5: Seed data for instant demo, README, buffer for bugs.

**Milestone:** Live at public URL. Demo-ready. Auth, evals, traces all working.

## 9. Risk Mitigations

| Risk | Mitigation |
|---|---|
| ag_ui_adk bridge issues | Dedicated time in Week 2. Fallback: direct FastAPI + WebSocket with CopilotKit custom backend |
| LLM judge cost spiral | Gemini Flash default (~$0.01/run). Token counting budget cap in eval engine |
| Neon + Cloud Run double cold start | Neon pgbouncer pooling. Both wake in parallel, not sequentially |
| DeepEval metric flakiness | Pin version. Cache results per (input, output) hash. Majority voting for near-threshold cases |
| Scope creep | No failure clustering, voice adapter, or BYOA HTTP adapter in MVP. All Phase 2 |

## 10. Phase 2 (Post-Validation)

- BYOA via `HTTPAgentAdapter` — user provides endpoint + auth
- Failure clustering — embed failing transcripts, HDBSCAN, LLM cluster labels
- Live human grading — async HITL during eval runs for uncertain judge outputs
- Voice adapter — ADK speech/streaming support
- Coding agent adapter — sandboxed execution in ephemeral containers
- A2UI payload rendering for rich result widgets
- Job queue (Upstash Redis) for concurrent eval runs
