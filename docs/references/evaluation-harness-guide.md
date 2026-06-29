# Evaluation Harness — Reference Guide

Saved from user-provided research. Key reference for project direction.

## Key Competitors
- **Arize AX** (https://arize.com/ax/) — Enterprise platform: Harness-as-Judge, managed agents, swarm observability, agent experiments, AI-native debugging
- **Arize Phoenix** (https://github.com/Arize-ai/phoenix) — Open-source: OTel tracing, LLM eval, datasets, experiments, prompt management. Python + TypeScript packages.
- **DeepEval** — pytest-native, 50+ metrics, Apache-2.0
- **Braintrust** — Commercial, deep tracing, CI gating
- **promptfoo** — CLI/YAML, red-teaming (acquired by OpenAI)

## Architecture Pattern (from research)
1. **Inputs**: traces, test cases, production samples
2. **Engine**: deterministic checks + LLM judges + embeddings
3. **Actions**: CI gates, alerts, annotations, feedback loops

## Key Insight
> "Plug-and-play is the onboarding funnel INTO a persistent workspace (harness), not a standalone flow."

## What Arize/Phoenix Has That We Need
- Workspace/project as the top-level container
- Persistent trace storage (OTel-native)
- Experiment tracking (compare runs over time)
- Dataset versioning (test suites as versioned assets)
- Adversarial/red-team testing
- pass@k (multiple runs for consistency)
- Statistical significance (confidence intervals)
