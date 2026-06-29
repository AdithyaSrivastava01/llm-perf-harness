# Plug-and-Play Eval Flow — Design Spec

## Overview

Add a "Lighthouse for AI Agents" flow to the existing harness: user pastes an agent endpoint URL, we auto-detect capabilities, generate tests, run evals, and return a graded report card — all in under 2 minutes with zero configuration. First eval free (shared judge key), BYOK after sign-in. Data isolated per user with `org_id` column for future multi-tenancy.

## Decision Log

| Decision | Chosen | Over | Why |
|---|---|---|---|
| Agent protocol | OpenAI-compatible default, custom schema fallback | Raw HTTP only, OpenAI only | 90% of deployed agents speak OpenAI format. Custom schema catches the rest without forcing everyone through mapping. |
| Auto-detection | Probe 3 messages + user confirms | User self-declares, probe only | Probing catches capabilities users miss. Confirmation prevents false classifications from wasting eval runs. |
| Report format | Two-tier: summary grade + expandable per-case detail | Grade only, detail only | Summary answers "is it good?" in 2 seconds. Detail answers "why did case 7 fail?" when they care. |
| BYOK model | First eval free (shared key), BYOK after | Always BYOK, always free | Zero-friction first eval hooks users. BYOK after sign-in is natural upgrade point. |
| Workspace isolation | User-level now, org_id column baked in | User only, full org model | User-level works today. org_id costs nothing to add, saves weeks when enterprises ask for teams. |

## 1. Quick Eval Flow

### Endpoint: `POST /api/quick-eval`

**Input:**
```json
{
  "endpoint_url": "https://my-agent.com/v1/chat/completions",
  "auth_header": "Bearer sk-...",
  "schema_type": "openai",
  "custom_schema": null,
  "judge_api_key": null
}
```

- `endpoint_url` (required): agent's HTTP endpoint
- `auth_header` (optional): authorization header value
- `schema_type`: `"openai"` (default) or `"custom"`
- `custom_schema`: JSON path mappings for custom APIs (only when `schema_type = "custom"`)
- `judge_api_key` (optional): user's own key for the judge model. If null, first eval uses shared key.

**Flow:**

```
1. CONNECT   → Validate endpoint reachable (POST with minimal payload, expect 200/400/401)
2. DETECT    → Send 3 probe messages, classify capabilities
3. CONFIRM   → Return detected capabilities to user for confirmation
   --- user confirms ---
4. GENERATE  → Auto-create test suite (5-10 cases) based on confirmed capabilities
5. EVAL      → Run suite with auto-selected metrics
6. REPORT    → Return graded report card
```

Steps 1-3: synchronous, ~10 seconds.
Steps 4-6: after user confirms, ~30-60 seconds.

**Meta-agent integration:** `quick_eval` and `connect_agent` are also meta-agent tools. Users trigger via chat ("evaluate my agent at https://...") OR the dedicated Quick Eval UI page. Same backend logic, two entry points.

## 2. HTTPAgentAdapter

New adapter implementing the existing `AgentAdapter` Protocol. Connects to any external agent via HTTP.

```python
class HTTPAgentAdapter:
    endpoint_url: str
    auth_header: str | None
    schema_type: str                  # "openai" | "custom"
    custom_schema: dict | None
    detected_capabilities: set[str]   # filled by auto-detect

    # AgentAdapter Protocol implementation
    agent_id -> str                   # "http-{hash(endpoint_url)}"
    display_name -> str               # user-provided or derived from URL
    capabilities -> set[str]          # from detection
    invoke(input, context) -> AgentResponse
    supported_metrics() -> list[str]  # derived from capabilities
    expected_tools() -> None          # unknown for external agents
    reference_contexts() -> None      # unknown for external agents
```

### OpenAI-Compatible Format (Default)

Request:
```json
POST {endpoint_url}
Headers: {"Authorization": "{auth_header}", "Content-Type": "application/json"}
Body: {
  "messages": [{"role": "user", "content": "..."}],
  "temperature": 0
}
```

Response parsing:
- `choices[0].message.content` → `AgentResponse.output`
- `choices[0].message.tool_calls` → `AgentResponse.tool_calls` (if present)
- Response latency → `AgentResponse.latency_ms`
- `usage.prompt_tokens` / `usage.completion_tokens` → `AgentResponse.token_usage`

### Custom Schema (Fallback)

User provides JSON path mappings:
```json
{
  "request": {
    "input_path": "query",
    "messages_format": "flat"
  },
  "response": {
    "output_path": "data.answer",
    "tool_calls_path": "data.actions",
    "latency_path": "meta.duration_ms"
  }
}
```

Adapter uses these paths to extract/insert data from the agent's native format.

## 3. Auto-Detection (Capability Probing)

Three probe messages sent sequentially to the agent:

| # | Probe Message | Detects | Signal |
|---|---|---|---|
| 1 | "What can you help me with?" | General capabilities | Mentions of tools, search, retrieval, code in response text |
| 2 | "What is 15 * 23 + 7?" | Tool use | `tool_calls` present in API response, or exact answer "352" suggesting calculator |
| 3 | "Based on your knowledge base, what information do you have?" | RAG / retrieval | Response references sources, documents, context, or retrieval |

**Classification logic:**
- `tool_calls` array present in any response → `{"tools"}`
- Response text mentions retrieval/sources/documents/context → `{"rag"}`
- All agents get `{"text"}` by default
- Multi-turn capability assumed (tested during eval, not during probe)

**Output:** detected capabilities + confidence level per capability, returned for user confirmation before eval proceeds.

## 4. Metric Auto-Selection

Based on confirmed capabilities, metrics are automatically selected:

| Capability | Metrics Selected | Backend |
|---|---|---|
| `text` only | `answer_relevancy`, `response_match_score` | DeepEval, ADK |
| `text` + `tools` | + `tool_trajectory_avg_score`, `final_response_match_v2` | ADK |
| `text` + `rag` | + `faithfulness`, `contextual_relevancy`, `hallucination` | DeepEval |
| `text` + `tools` + `rag` | All of the above | Both |

Thresholds use sensible defaults (same as existing `_default_metrics` in registry).

## 5. Report Card

### Summary Tier (Always Visible)

```
┌──────────────────────────────────┐
│  Agent Quality Grade:  B+  (82%) │
│                                  │
│  Tool Accuracy     ██████── 95%  │
│  Response Quality  █████─── 78%  │
│  Faithfulness      █████─── 85%  │
│                                  │
│  Pass Rate:  9/10                │
│  Avg Latency: 340ms              │
│  Eval Time: 45s                  │
└──────────────────────────────────┘
```

**Grade mapping:**
- A: 90-100% (excellent)
- B: 80-89% (good)
- C: 70-79% (needs improvement)
- D: 60-69% (poor)
- F: <60% (failing)

Grade = weighted average of all metric scores, weighted by metric importance.

### Detail Tier (Expandable Per Test Case)

Each test case expands to show:
- Input message(s)
- Agent's actual response
- Expected output (if applicable)
- Per-metric scores with pass/fail badge
- Tool calls made (if any)
- Latency for this case

### Regression View (After Second Eval)

When user re-evaluates after changes:
- Side-by-side score comparison
- Green/red deltas per metric
- "Your faithfulness dropped 12%" callouts
- One-click baseline promotion

## 6. BYOK + Free Tier

### First Eval (No Auth Required)
- Uses shared Gemini Flash key owned by the harness
- Rate-limited: 1 eval per 10 minutes per IP
- Max 5 test cases per quick eval
- No results stored (ephemeral)

### After Sign-In (BYOK)
- User provides their own Gemini or OpenAI API key
- Key encrypted with `HARNESS_ENCRYPTION_KEY` (Fernet symmetric encryption)
- Stored in `user_settings` table
- Key never logged, never in traces, never in eval results
- Unlimited evals, results stored, baselines available
- Can choose judge provider: Gemini Flash (default) or GPT-4o

### Key Storage
```python
from cryptography.fernet import Fernet

# Encrypt before storing
fernet = Fernet(settings.encryption_key)
encrypted = fernet.encrypt(api_key.encode())

# Decrypt when needed for eval
decrypted = fernet.decrypt(encrypted).decode()
```

## 7. Data Model Changes

### Modify Existing Tables

```sql
-- Add org_id to users (nullable for now)
ALTER TABLE users ADD COLUMN org_id uuid;
```

### New Tables

```sql
-- BYOK key storage
user_settings (
    user_id             uuid PRIMARY KEY REFERENCES users,
    judge_provider      text DEFAULT 'gemini',
    judge_api_key_enc   text,
    settings            jsonb DEFAULT '{}',
    updated_at          timestamptz DEFAULT now()
);

-- Connected external agents (BYOA)
connected_agents (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 uuid NOT NULL REFERENCES users,
    endpoint_url            text NOT NULL,
    auth_header_enc         text,
    schema_type             text NOT NULL DEFAULT 'openai',
    custom_schema           jsonb,
    detected_capabilities   text[],
    confirmed_capabilities  text[],
    display_name            text,
    last_probed_at          timestamptz,
    created_at              timestamptz DEFAULT now()
);
```

### Indexes
- `connected_agents(user_id)` — list user's agents
- `connected_agents(user_id, endpoint_url)` — prevent duplicates

## 8. New Meta-Agent Tools

| Tool | Purpose |
|---|---|
| `connect_agent` | Takes endpoint URL + auth, runs probe, returns detected capabilities |
| `quick_eval` | Takes agent_id (from connect) + confirmed capabilities, generates tests, runs eval, returns report |

These integrate with the existing meta-agent. Users can do the full plug-and-play flow via chat.

## 9. New Frontend Pages

### Quick Eval Page (`/quick-eval`)
- URL input + optional auth token field
- "Scan Agent" button → shows probe results
- Capability confirmation checkboxes
- "Run Eval" button → streams progress → shows report card
- No auth required for first eval

### Report Card Component
- Reusable component showing grade + metrics + per-case detail
- Used in Quick Eval page AND in chat (via CopilotKit action rendering)

## 10. What Changes vs Current Build

| Existing Component | Change |
|---|---|
| `AgentAdapter` Protocol | No change |
| Eval engine | No change |
| Metric routing | No change |
| Meta-agent | Add `connect_agent` + `quick_eval` tools |
| Data model | Add `org_id` column, `user_settings` + `connected_agents` tables |
| Frontend | Add `/quick-eval` page + report card component |
| Config | Add `HARNESS_ENCRYPTION_KEY` env var |
| Dependencies | Add `cryptography` (Fernet encryption) |

Everything additive. No rewrites of existing code.

## 11. Testing

| Layer | What to Test |
|---|---|
| Unit | HTTPAgentAdapter parsing (OpenAI format + custom schema), capability detection classification logic, grade calculation, encryption/decryption |
| Integration | Full probe → detect → eval flow with mock HTTP agent, BYOK key storage + retrieval |
| E2E | `/api/quick-eval` endpoint, Quick Eval page renders report |
