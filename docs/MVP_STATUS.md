# Sentinel AI — MVP Status Report

> Generated: August 24, 2026
> Updated: August 24, 2026 — Bug fixes applied (Dockerfile, Slack MCP, Terraform, Jira MCP added)
> This document tracks what exists in the codebase today, what's partially implemented, and what needs to be built next — prioritized by impact.

---

## Executive Summary

**What exists:** A fully functional MVP with 98 files, ~9,800 lines of Python. The core event-driven architecture works, the AI orchestrator runs 6 specialized agents in simulation mode, and every external integration has a simulation fallback. You can `pip install -e .` and run the entire AI analysis pipeline without any API keys, Docker, or database.

**What's missing:** The workflow engine, real Kubernetes/GitHub/Jira connectivity, end-to-end integration tests, and a React dashboard.

---

## Component Status Matrix

| Component | Status | Files | Notes |
|-----------|--------|-------|-------|
| **Shared Infrastructure** | ✅ Complete | 6 | Config, DB, Kafka, Redis, events, exceptions |
| **Incident Service** | ✅ Complete | 5 | Models, schemas, service, publisher, consumer |
| **Deployment Service** | ✅ Complete | 5 | Models, schemas, service, publisher, consumer |
| **Kubernetes Simulator** | ✅ Complete | 4 | 4 failure scenarios, realistic pod/deployment state |
| **Log Collector** | ✅ Complete | 2 | Ingest, query, timeline, simulation |
| **Metrics Collector** | ✅ Complete | 2 | Snapshot, range queries, timeline generation |
| **API Gateway** | ✅ Complete | 8 | FastAPI, REST, WebSocket, middleware, routes |
| **AI Orchestrator** | ✅ Complete | 10 | LangGraph graph, 6 agents, dual-mode LLM |
| **MCP Tools** | ✅ Complete | 7 | K8s, GitHub, Jira, Prometheus, Slack tool servers |
| **Infrastructure** | ⚠️ Partial | 11 | Docker + K8s manifests complete; Terraform partial |
| **Tests** | ⚠️ Partial | 8 | Unit tests only; no integration or E2E tests |
| **Scripts** | ✅ Complete | 3 | Simulate, seed, run analysis |
| **Documentation** | ✅ Complete | 9 | Architecture, guides, ADRs, checklists |
| **Workflow Engine** | ❌ Not Started | 0 | Referenced in docs but no code exists |
| **Jira MCP** | ✅ Complete | 1 | create_issue, add_comment, update_status (simulation mode) |
| **React Dashboard** | ❌ Not Started | 0 | Not started (backend-only MVP) |
| **CI/CD Pipeline** | ❌ Not Started | 0 | No GitHub Actions workflows |
| **OpenSearch Integration** | ❌ Not Started | 0 | Referenced in architecture, not implemented |

---

## Detailed Component Analysis

### 1. Shared Infrastructure ✅
**What exists:**
- `services/shared/config.py` — Pydantic Settings with 8 sub-configurations (Database, Redis, Kafka, LLM, GitHub, Jira, Slack, K8s, Observability)
- `services/shared/database.py` — Async SQLAlchemy 2.0 engine, session factory, dependency injection
- `services/shared/kafka.py` — Async producer with retry+DLQ, consumer base class with idempotency
- `services/shared/redis.py` — Async Redis with caching, distributed locks (Lua script)
- `services/shared/events.py` — 9 event types with Pydantic models, topic registry, discriminator-based union
- `services/shared/exceptions.py` — 8 exception classes (NotFound, Database, Kafka, AI, External, Workflow)

**Accuracy notes:**
- Architecture doc correctly describes this layer

### 2. AI Orchestrator ✅
**What exists:**
- `services/ai/orchestrator.py` — LangGraph StateGraph with 6 nodes
- `services/ai/state.py` — AgentState with LangGraph `add_messages` annotation
- `services/ai/llm.py` — Dual-mode: OpenAI, Anthropic, or deterministic simulation
- 6 agents: log, k8s, metrics, deployment, root cause, remediation
- Prompt templates in `services/ai/prompts/` (4 files)
- 4 prompt template files exist but are NOT imported by the agents

**Accuracy notes:**
- **Architecture doc says "8 agents"** but only **6 agents** exist. Jira and GitHub agents are mentioned in the original spec but were never built.
- **Prompts directory exists** with 4 files (`log_analysis.py`, `k8s_analysis.py`, `metrics_analysis.py`, `root_cause.py`) but agents define their prompts inline and don't import from this directory. The prompt files are unused.
- Graph structure matches docs (parallel fan-out → root cause → remediation → END)
- All agents call `LLMClient().analyze()` then `LLMClient().analyze_structured()` — making two LLM calls per agent. This could be optimized.

### 3. MCP Integration ✅
**What exists:**
- `services/mcp/server.py` — Tool registry with 17 tools across 4 categories
- `services/mcp/client.py` — Convenience methods for all tools
- K8s tools: get_pods, describe_deployment, get_events, get_logs, get_configmap
- GitHub tools: create_pull_request, create_issue, get_recent_commits
- Prometheus tools: query_instant, query_range
- Slack tools: send_message, send_incident_alert

**Accuracy notes:**
- **Bug:** `slack.py` `send_message()` has duplicate `message` key in return dict
- All tools are in **simulation mode** — no real HTTP/API calls
- No Jira MCP tools exist (despite Jira config in settings and mentions in docs)

### 4. API Gateway ✅
**What exists:**
- `services/gateway/main.py` — FastAPI app factory with lifespan, CORS, request middleware, exception handlers
- Routes: health, incidents (CRUD + simulate + analyze + WebSocket), deployments (CRUD + simulate), analysis (run + simulate)
- Dependency injection for DB, Redis, Kafka

**Accuracy notes:**
- **`/ready` probe** imports `sqlalchemy` at runtime via `__import__("sqlalchemy")` — works but is fragile
- WebSocket endpoint exists but doesn't auto-push analysis events — only responds to "ping"
- Deployment service `update_status()` doesn't create a new `DeploymentUpdate` schema, so the `PATCH /deployments/{id}` route is missing (only simulate and create exist)

### 5. Infrastructure ⚠️
**What exists:**
- Dockerfile (multi-stage) — has a build bug: `pip install --no-cache-dir --no-deps .` won't install dependencies
- docker-compose.yml (full stack: app + postgres + redis + kafka + zookeeper + prometheus + grafana)
- docker-compose.minimal.yml (app + postgres + redis + kafka)
- Prometheus config
- K8s manifests: Deployment (with probes, resources, anti-affinity), ConfigMap, Secrets template, Service, Ingress, ServiceAccount, RBAC

**Accuracy notes:**
- **Terraform `main.tf` references modules that don't exist:** `module.rds` and `module.elasticache` are declared but only `modules/vpc/` and `modules/ecs/` directories exist
- **Dockerfile bug:** The builder stage runs `pip install --no-deps .` which installs the package itself without dependencies. Should be `pip install .` or use `pip install` with the full deps list.
- **K8s RBAC:** The `ClusterRole` and `ClusterRoleBinding` definitions are in the same file as the Service and ServiceAccount, missing YAML `---` separator between them. All are in `services/sentinel-service.yaml` which is fine structurally but semantically mixed.
- **Prometheus config** scrapes `sentinel:8000/metrics` but the app doesn't have a `/metrics` endpoint

### 6. Tests ⚠️
**What exists (8 test files):**
- `test_config.py` — 10 tests for settings validation
- `test_events.py` — 12 tests for event models and serialization
- `test_k8s_simulator.py` — 9 tests for all 4 K8s failure scenarios
- `test_llm_simulation.py` — 11 tests for simulation mode (text + structured)
- `test_ai_state.py` — 8 tests for AgentState and related models
- `test_collector.py` — 10 tests for log and metrics collectors

**What's missing:**
- Integration tests (API routes + database)
- End-to-end tests (full pipeline: create incident → trigger analysis → verify results)
- Consumer tests (Kafka event handling)
- MCP tool tests
- No test coverage reporting configured

### 7. Documentation ✅
**What exists:**
- Architecture README with 4 Mermaid diagrams
- Event flow diagrams
- Development guide
- Deployment guide
- 3 ADRs (simulation mode, event-driven, multi-agent)
- Phase checklist
- Project README

**Inaccuracies found (all fixed):**
1. ~~Architecture doc says "6 AI Agents" in the Mermaid diagram but the text says 8~~ → **Fixed**
2. ~~Architecture doc lists "Workflow Engine" as a microservice~~ → **Fixed** (marked as planned)
3. ~~Development guide lists `services/workflow/` in project structure~~ → **Fixed** (marked as planned)
4. ~~Phase checklist marks all phases ✅~~ → **Fixed** (workflow engine marked ❌)
5. ~~README says system can "Create Jira tickets and pull requests"~~ → **Fixed** (clarified as simulation)
6. ~~Architecture doc lists "OpenSearch" in data layer~~ → **Fixed** (replaced with in-memory logs)
7. ~~Architecture doc says "ELK" in observability~~ → **Fixed** (removed)
8. ~~Terraform docs reference `module.rds` and `module.elasticache`~~ → **Fixed** (commented out with TODOs)

---

## Bugs Found

| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `services/mcp/tools/slack.py` | Duplicate `message` key in `send_message()` return dict | Low | ✅ Fixed |
| 2 | `infrastructure/docker/Dockerfile` | `pip install --no-cache-dir --no-deps .` skips all dependencies | High | ✅ Fixed |
| 3 | `services/ai/prompts/` (4 files) | Prompt templates exist but agents define prompts inline — unused files | Low | ⚠️ Open |
| 4 | `services/gateway/routes/health.py` | `__import__("sqlalchemy")` at runtime is fragile | Low |
| 5 | `infrastructure/terraform/main.tf` | References non-existent `modules/rds` and `modules/elasticache` | Medium | ✅ Fixed |
| 6 | `services/gateway/routes/deployments.py` | No `PATCH /deployments/{id}` route (only create + list + get + simulate) | Low | ⚠️ Open |

---

## What Needs to Be Built Next (Priority Order)

### P0 — Critical (blocks usability) — ✅ All Complete

1. ~~Fix Dockerfile~~ — ✅ Done
2. ~~Fix Slack MCP tool~~ — ✅ Done
3. ~~Add Jira MCP tool~~ — ✅ Done
4. ~~Fix Terraform modules~~ — ✅ Done (commented out with TODOs)

### P1 — High (core feature gaps)

5. **Workflow Engine** — `services/workflow/` is referenced everywhere but empty. Implement:
   - Saga pattern for remediation workflows (auto-rollback, config-fix, scale)
   - Step execution engine with approval gates
   - Workflow state machine
6. **Integration Tests** — Test API routes with database, test consumers with Kafka
7. **End-to-End Tests** — Full pipeline: simulate incident → AI analysis → verify output
8. **Real MCP Connectivity** — Wire K8s tools to real `kubectl` via `subprocess` or `kubernetes` Python client
9. **GitHub MCP Real Mode** — Use `httpx` to call GitHub API when `GITHUB_TOKEN` is set

### P2 — Medium (polish and production-readiness)

10. **Deployment `PATCH` route** — Add `PATCH /deployments/{id}` for status updates
11. **WebSocket analysis stream** — Auto-push agent progress to WebSocket subscribers
12. **Circuit breaker** — Add `tenacity` circuit breaker for external service calls
13. **OpenTelemetry integration** — Add distributed tracing to the FastAPI app
14. **CI/CD Pipeline** — GitHub Actions for testing, linting, and Docker image building
15. **Metrics endpoint** — Add `/metrics` for Prometheus scraping
16. **Alembic migration testing** — Verify migration forward/backward

### P3 — Nice-to-have (future features)

17. **React Dashboard** — Incident timeline, agent progress, metrics visualization
18. **Event sourcing for incident timeline** — Already partially done via `IncidentEvent` model
19. **OpenSearch integration** — Replace in-memory log collector with real search
20. **Similar incident retrieval (RAG)** — Embedding-based search over past incidents
21. **Blast-radius estimation** — Impact analysis for proposed fixes
22. **Deployment risk scoring** — Predictive risk scoring before deployment
23. **Grafana dashboards** — Pre-built dashboards for incident and deployment metrics

---

## How to Use & Test the MVP Today

### Quick Start (Zero Dependencies)

```bash
cd sentinel-ai

# Install
pip install -e ".[dev]"

# Run the full AI analysis pipeline (no DB, no Kafka, no API keys needed)
python -m scripts.run_analysis --scenario missing_env_var

# Simulate a full incident lifecycle
python -m scripts.simulate_incident --scenario out_of_memory

# Run all unit tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=services --cov-report=term-missing
```

### Full Stack (Docker)

```bash
# Start infrastructure
docker compose -f docker-compose.minimal.yml up -d

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start the API server
uvicorn services.gateway.main:app --reload --host 0.0.0.0 --port 8000

# Open API docs
open http://localhost:8000/docs
```

### API Testing

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Simulate a deployment failure
curl -X POST "http://localhost:8000/api/v1/deployments/simulate?service_name=sentinel-api&failure_reason=missing_env_var"

# 3. Get the deployment (note the ID from step 2)
curl http://localhost:8000/api/v1/deployments

# 4. Get simulated analysis
curl "http://localhost:8000/api/v1/analysis/simulate?scenario=missing_env_var"
```

### Enable Real AI

```bash
# Option A: OpenAI
export OPENAI_API_KEY=sk-...
python -m scripts.run_analysis

# Option B: Anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python -m scripts.run_analysis
```

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Total files | 97 |
| Python source files | 70 (59 services + 8 tests + 3 scripts) |
| Infrastructure files | 11 |
| Documentation files | 9 |
| Root config files | 6 |
| Lines of code | ~9,600 |
| Unit test count | ~60 |
| Test files | 8 |
| AI agents | 6 |
| MCP tools | 17 |
| API routes | 13 |
| K8s failure scenarios | 4 |
| Supported LLM providers | 3 (OpenAI, Anthropic, Simulation) |

---

## File Count by Category

```
services/shared/     7 files   (config, db, kafka, redis, events, exceptions, __init__)
services/gateway/    9 files   (main, deps, 4 routes, 3 __init__)
services/incident/   6 files   (models, schemas, service, publisher, consumer, __init__)
services/deployment/ 6 files   (models, schemas, service, publisher, consumer, __init__)
services/kubernetes/ 4 files   (simulator, models, consumer, __init__)
services/collector/  3 files   (log_collector, metrics_collector, __init__)
services/ai/        11 files   (orchestrator, llm, state, 6 agents, __init__)
services/ai/prompts/ 5 files   (4 prompts, __init__)  [UNUSED]
services/mcp/        9 files   (server, client, 4 tools, __init__)
services/workflow/   0 files   [EMPTY — planned but not implemented]
tests/               8 files
scripts/             3 files
docs/                9 files
infrastructure/     11 files   (docker, k8s, terraform)
```
