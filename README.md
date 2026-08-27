# 🛡️ Sentinel AI — Autonomous Cloud Operations Platform

> An AI-powered Site Reliability Engineer that continuously monitors cloud infrastructure, investigates incidents, explains failures, and proposes fixes.

**This is not a chatbot.** It's a distributed platform where AI is one component in a larger event-driven system.

---

## What It Does

When a deployment fails at 2:30 AM, instead of paging someone:

1. **Detects** the failure (CrashLoopBackOff, OOMKilled, 503s)
2. **Collects** evidence from logs, Kubernetes, metrics, and deployment history
3. **Analyzes** the data using 6 specialized AI agents running in parallel
4. **Identifies** the root cause with confidence scoring
5. **Proposes** remediation actions ranked by risk level
6. **Simulates** Jira ticket creation and GitHub pull requests (real integrations planned)
7. **Orchestrates** safe recovery workflows (workflow engine planned)

## Architecture

```
                    React Dashboard (planned)
                           │
                   API Gateway (FastAPI)
  ────────────────────────────────────────────────
  Incident Service │ Deployment Service │ K8s Simulator
  AI Orchestrator  │ Workflow Engine    │ Collectors
     (6 agents)     (planned)
  ────────────────────────────────────────────────
                    Kafka Event Bus
  ────────────────────────────────────────────────
  PostgreSQL │ Redis │ In-Memory Logs (simulated)
  ────────────────────────────────────────────────
  Prometheus │ Grafana
  ────────────────────────────────────────────────
                    Kubernetes + Terraform (AWS)
```

### Multi-Agent AI Pipeline

```
                    ┌──→ Log Agent ──────────┐
                    │                        │
  Start ──→ fan_out ──→ K8s Agent ──────────┤──→ Root Cause Agent ──→ Remediation Agent ──→ END
                    │                        │
                    ├──→ Metrics Agent ──────┤
                    │                        │
                    └──→ Deployment Agent ───┘
```

### Event-Driven Communication

Every action emits an event through Kafka:

```
DeploymentCreated → Kafka → Deployment Service
       ↓
PodFailed → Kafka → Incident Service
       ↓
AI Analysis Started → Kafka → Notification Service
       ↓
PR Generated → Kafka → Approval Requested → Deploy Fix
```

## Quick Start

### Zero-Config Demo (No API Keys Needed)

```bash
# Clone
git clone https://github.com/your-org/sentinel-ai.git
cd sentinel-ai

# Install
pip install -e ".[dev]"

# Run the full AI analysis pipeline in simulation mode
python -m scripts.run_analysis --scenario missing_env_var

# Or simulate an incident end-to-end
python -m scripts.simulate_incident

# Run tests
pytest tests/ -v
```

### Full Stack with Docker

```bash
# Start everything (PostgreSQL, Redis, Kafka, Prometheus, Grafana)
docker compose up -d

# Open the API docs
open http://localhost:8000/docs

# Simulate a deployment failure
curl -X POST "http://localhost:8000/api/v1/deployments/simulate?service_name=sentinel-api&failure_reason=missing_env_var"

# Trigger AI analysis
curl -X POST "http://localhost:8000/api/v1/analysis/run?incident_id=<incident-id>"
```

### Enable Real AI

```bash
# Option A: OpenAI
export OPENAI_API_KEY=sk-...

# Option B: Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Restart — agents now use real LLM for analysis
python -m scripts.run_analysis
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript (planned) |
| API | FastAPI (Python 3.11+) |
| AI Agents | LangGraph + LangChain |
| MCP Integration | Model Context Protocol |
| Event Bus | Apache Kafka (aiokafka) |
| Cache | Redis |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Tracing | OpenTelemetry (planned) |
| Containers | Docker |
| Orchestration | Kubernetes |
| Infrastructure | Terraform (AWS) |
| CI/CD | GitHub Actions (planned) |

## Project Structure

```
sentinel-ai/
├── services/
│   ├── shared/          # Config, DB, Kafka, Redis, events, exceptions
│   ├── gateway/         # FastAPI app + REST/WebSocket routes
│   ├── incident/        # Incident CRUD, state machine, Kafka integration
│   ├── deployment/      # Deployment tracking, rollback management
│   ├── kubernetes/      # K8s cluster state simulator
│   ├── collector/       # Log & metrics collectors
│   ├── ai/              # LangGraph orchestrator + 6 specialized agents
│   ├── mcp/             # MCP tool servers (K8s, GitHub, Jira, Prometheus, Slack)
│   └── workflow/        # Workflow engine (planned)
├── infrastructure/
│   ├── docker/          # Dockerfile, Prometheus config
│   ├── kubernetes/      # K8s manifests (Deployment, ConfigMap, Service, RBAC)
│   └── terraform/       # AWS VPC + ECS modules
├── tests/               # pytest test suite
├── scripts/             # Simulation, seeding, analysis scripts
├── docs/                # Architecture, guides, ADRs, checklists
├── alembic/             # Database migrations
└── docker-compose.yml   # Full development stack
```

## Documentation

- [Architecture](docs/architecture/README.md) — System design with Mermaid diagrams
- [Development Guide](docs/guides/development.md) — Setup, project structure
- [Usage & Testing Guide](docs/guides/testing.md) — How to use, test, and demo the MVP
- [Deployment Guide](docs/guides/deployment.md) — Docker, K8s, Terraform deployment
- [MVP Status Report](docs/MVP_STATUS.md) — What exists, what's next, bugs found
- [ADRs](docs/decisions/) — Architecture Decision Records
- [Phase Checklist](docs/tracking/phase-checklist.md) — Full implementation tracking

## License

MIT
