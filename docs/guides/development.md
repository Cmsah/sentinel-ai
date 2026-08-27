# Development Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/your-org/sentinel-ai.git
cd sentinel-ai
cp .env.example .env
```

### 2. Start infrastructure (minimal mode)

```bash
docker compose -f docker-compose.minimal.yml up -d
```

This starts PostgreSQL, Redis, and Kafka.

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn services.gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Explore the API

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

## Running Without Any API Keys

Sentinel AI has a full **simulation mode** that works without any external services:

```bash
# Run the full analysis pipeline in simulation mode
python -m scripts.run_analysis --scenario missing_env_var

# Simulate an incident end-to-end
python -m scripts.simulate_incident --scenario out_of_memory

# Seed the database with sample data
python -m scripts.seed_data --count 10
```

## Project Structure

```
sentinel-ai/
├── services/
│   ├── shared/          # Shared infra (config, DB, Kafka, Redis, events)
│   ├── gateway/         # FastAPI application + routes
│   ├── incident/        # Incident service (models, service, consumer, publisher)
│   ├── deployment/      # Deployment service
│   ├── kubernetes/      # K8s state simulator
│   ├── collector/       # Log and metrics collectors
│   ├── ai/              # AI orchestrator + agents
│   │   ├── agents/      # 6 specialized agents
│   │   ├── prompts/     # Agent prompt templates
│   │   ├── llm.py       # Dual-mode LLM client
│   │   ├── state.py     # LangGraph state definitions
│   │   └── orchestrator.py  # Graph orchestration
│   ├── mcp/             # MCP tool servers
│   │   └── tools/       # K8s, GitHub, Jira, Prometheus, Slack tools
│   └── workflow/        # Workflow engine (planned)
├── infrastructure/
│   ├── docker/          # Dockerfile, Prometheus config
│   ├── kubernetes/      # K8s manifests (deployments, configmaps, services)
│   └── terraform/       # AWS infrastructure (VPC, ECS)
├── tests/               # Test suite
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── alembic/             # Database migrations
├── docker-compose.yml   # Full development stack
└── pyproject.toml       # Project configuration
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=services --cov-report=html

# Run specific test file
pytest tests/test_llm_simulation.py -v
```

## API Endpoints

### Health
- `GET /health` — Liveness probe
- `GET /ready` — Readiness probe

### Incidents
- `POST /api/v1/incidents` — Create incident
- `GET /api/v1/incidents` — List incidents (with filters)
- `GET /api/v1/incidents/{id}` — Get incident detail + timeline
- `PATCH /api/v1/incidents/{id}` — Update incident
- `POST /api/v1/incidents/{id}/analyze` — Trigger AI analysis
- `POST /api/v1/incidents/simulate` — Simulate incident for demo

### Deployments
- `POST /api/v1/deployments` — Record deployment
- `GET /api/v1/deployments` — List deployments
- `GET /api/v1/deployments/{id}` — Get deployment detail
- `POST /api/v1/deployments/simulate` — Simulate deployment failure

### AI Analysis
- `POST /api/v1/analysis/run` — Run full AI analysis on an incident
- `GET /api/v1/analysis/simulate` — Get simulated analysis results

### WebSocket
- `WS /ws/incidents/{id}` — Live incident update stream

## Configuration

All configuration is managed through environment variables (see `.env.example`).

Key settings:
- `APP_ENV` — `development`, `staging`, `production`, `test`
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `KAFKA_BOOTSTRAP_SERVERS` — Kafka broker addresses
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — LLM provider keys (optional — simulation mode works without them)
