# Usage & Testing Guide

> How to use, test, and demo Sentinel AI as of the MVP release.

---

## Quick Reference

| What you want to do | Command |
|---------------------|---------|
| Install the project | `pip install -e ".[dev]"` |
| Run AI analysis (no API keys) | `python -m scripts.run_analysis --scenario missing_env_var` |
| Simulate full incident lifecycle | `python -m scripts.simulate_incident --scenario out_of_memory` |
| Run unit tests | `pytest tests/ -v` |
| Start the API server | `uvicorn services.gateway.main:app --reload --port 8000` |
| Start with Docker | `docker compose up -d` |

---

## 1. Zero-Config Demo (No API Keys, No Database)

This is the fastest way to see Sentinel AI in action. Every component has a simulation fallback, so you can run the full AI analysis pipeline with just Python and pip.

### Install

```bash
cd sentinel-ai
pip install -e ".[dev]"
```

### Run AI Analysis

The `run_analysis` script creates an in-memory incident, runs all 6 AI agents, and prints the results:

```bash
# Available scenarios: missing_env_var, out_of_memory, image_pull_error, application_error
python -m scripts.run_analysis --scenario missing_env_var
```

**What happens under the hood:**
1. The K8s simulator creates a deployment with the specified failure
2. The log collector generates realistic failure logs
3. The metrics collector generates a metrics snapshot
4. 4 analysis agents run in parallel (log, K8s, metrics, deployment)
5. The root cause agent synthesizes findings
6. The remediation agent proposes fixes

### Simulate Full Incident Lifecycle

```bash
# Creates incident → runs analysis → generates timeline → proposes fix
python -m scripts.simulate_incident --scenario out_of_memory
```

### Seed the Database

If you have a database running, you can seed it with sample data:

```bash
python -m scripts.seed_data --count 10
```

---

## 2. Running with Docker

### Minimal Stack (App + PostgreSQL + Redis + Kafka)

```bash
docker compose -f docker-compose.minimal.yml up -d

# Wait for services to be ready (~30 seconds)
docker compose -f docker-compose.minimal.yml logs -f sentinel
```

### Full Stack (All Observability)

```bash
docker compose up -d
# This starts: app, postgres, redis, kafka, zookeeper, prometheus, grafana
```

### Verify

```bash
# Health check
curl http://localhost:8000/health

# Readiness (checks DB + Redis connectivity)
curl http://localhost:8000/ready

# Open API docs
open http://localhost:8000/docs
```

---

## 3. API Usage

### Create an Incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Pod CrashLoopBackOff in production",
    "severity": "critical",
    "service": "sentinel-api",
    "description": "Pods are crash looping after deployment #812"
  }'
```

### List Incidents

```bash
# All incidents
curl http://localhost:8000/api/v1/incidents

# Filter by severity
curl "http://localhost:8000/api/v1/incidents?severity=critical"
```

### Simulate a Deployment Failure

```bash
# Creates a simulated deployment + auto-generates an incident
curl -X POST "http://localhost:8000/api/v1/deployments/simulate?service_name=sentinel-api&failure_reason=missing_env_var"
```

Available failure reasons: `missing_env_var`, `out_of_memory`, `image_pull_error`, `application_error`

### Run AI Analysis

```bash
# Simulated analysis (no LLM needed)
curl "http://localhost:8000/api/v1/analysis/simulate?scenario=missing_env_var"

# Real analysis (requires incident_id from a created incident)
curl -X POST "http://localhost:8000/api/v1/analysis/run?incident_id=<incident-id>"
```

### Simulate an Incident

```bash
curl -X POST "http://localhost:8000/api/v1/incidents/simulate?service_name=sentinel-api&failure_type=pod_crash_loop"
```

### WebSocket (Live Updates)

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/incidents/<incident-id>");
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

---

## 4. Running Tests

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=services --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ -v --cov=services --cov-report=html
open htmlcov/index.html
```

### Specific Test Suites

```bash
# Configuration validation
pytest tests/test_config.py -v

# Event model serialization
pytest tests/test_events.py -v

# K8s failure scenarios
pytest tests/test_k8s_simulator.py -v

# LLM simulation mode
pytest tests/test_llm_simulation.py -v

# AI state management
pytest tests/test_ai_state.py -v

# Log & metrics collectors
pytest tests/test_collector.py -v
```

### Test Coverage Summary

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_config.py` | 10 | Pydantic Settings validation, defaults, env overrides |
| `test_events.py` | 12 | Event models, serialization, topic registry, discriminator union |
| `test_k8s_simulator.py` | 9 | All 4 failure scenarios (missing env, OOM, image pull, app error) |
| `test_llm_simulation.py` | 11 | LLM simulation mode (text + structured output) |
| `test_ai_state.py` | 8 | AgentState, AgentFinding, AnalysisResult, RemediationAction models |
| `test_collector.py` | 10 | Log collector (ingest, query, timeline) + Metrics collector (snapshot, range) |
| **Total** | **~60** | Core logic, no external dependencies required |

### What Tests DON'T Cover (MVP Gaps)

- ❌ Integration tests (API routes + database)
- ❌ End-to-end tests (full pipeline: incident → analysis → results)
- ❌ Kafka consumer tests
- ❌ MCP tool tests
- ❌ WebSocket tests

---

## 5. Understanding the Simulation Mode

Sentinel AI is designed to run fully offline. Here's how each component simulates:

| Component | Simulation Behavior |
|-----------|-------------------|
| **LLM** | Deterministic responses based on input keywords (no API call) |
| **Kubernetes** | In-memory state machine with 4 failure scenarios |
| **Logs** | Generated log entries matching the failure scenario |
| **Metrics** | Synthetic CPU/memory/latency data matching failure patterns |
| **Prometheus** | Returns pre-configured metric values |
| **GitHub** | Returns mock PR/issue/commit data |
| **Jira** | Returns mock issue key and URL |
| **Slack** | Returns simulated message with preview |

### To Use Real LLM

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Restart the server — agents now use real LLM
uvicorn services.gateway.main:app --reload --port 8000
```

---

## 6. Demo Script (Presenting the Project)

### 5-Minute Demo

```bash
# Terminal 1: Start the server
uvicorn services.gateway.main:app --reload --port 8000

# Terminal 2: Run the demo

# Step 1: Show the health check
curl http://localhost:8000/health

# Step 2: Simulate a deployment failure (auto-creates incident)
curl -X POST "http://localhost:8000/api/v1/deployments/simulate?service_name=payment-service&failure_reason=missing_env_var"

# Step 3: List the incidents (show the auto-created one)
curl http://localhost:8000/api/v1/incidents | python -m json.tool

# Step 4: Run AI analysis on the latest incident
curl "http://localhost:8000/api/v1/analysis/simulate?scenario=missing_env_var" | python -m json.tool

# Step 5: Open the Swagger UI
open http://localhost:8000/docs
```

### What to Highlight

1. **Event-driven architecture**: Show how a deployment failure auto-creates an incident via Kafka
2. **Multi-agent AI**: Explain the fan-out → root cause → remediation pipeline
3. **Simulation mode**: Show the same demo works without any API keys
4. **MCP integration**: Show `SentinelMCPServer().list_tools()` to display all 20 MCP tools

---

## 7. Code Walkthrough

### Key Entry Points

| File | Purpose |
|------|---------|
| `services/gateway/main.py` | FastAPI app factory — start here |
| `services/ai/orchestrator.py` | LangGraph graph — the AI pipeline |
| `services/ai/llm.py` | Dual-mode LLM client |
| `services/kubernetes/simulator.py` | K8s failure simulation |
| `services/mcp/server.py` | MCP tool catalog |
| `scripts/run_analysis.py` | Standalone AI analysis script |

### Architecture Flow

```
API Request → FastAPI Router → Service Layer → Kafka Event → Consumer → AI Analysis
                                                                    ↓
                                                              6 Agents (parallel)
                                                                    ↓
                                                              Root Cause Synthesis
                                                                    ↓
                                                              Remediation Proposal
                                                                    ↓
                                                              Incident Updated
```

---

## 8. Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic'"
→ Ensure you're using Python 3.12+ with pydantic v2: `pip install "pydantic>=2.9.0"`

### "ModuleNotFoundError: No module named 'langgraph'"
→ Install AI dependencies: `pip install langgraph langchain-core`

### Tests fail with import errors
→ Install dev dependencies: `pip install -e ".[dev]"`

### Docker containers won't start
→ Check ports: `docker compose ps`. Ensure 5432 (postgres), 6379 (redis), 9092 (kafka) are free.

### "Connection refused" on Kafka
→ Kafka takes ~30 seconds to start. Wait and retry: `docker compose logs kafka`

---

## 9. File Inventory (MVP)

```
100 files total
73 Python source files
  - 59 service files (services/)
  - 8 test files (tests/)
  - 3 script files (scripts/)
  - 3 alembic files (alembic/)
11 infrastructure files (Docker, K8s, Terraform, Prometheus)
9 documentation files (docs/)
7 root config files (pyproject.toml, docker-compose, .env, etc.)
```
