# Sentinel AI — Architecture

## System Overview

Sentinel AI is an autonomous cloud operations platform that monitors infrastructure, investigates incidents, explains failures, and proposes fixes using a multi-agent AI system.

## High-Level Architecture

> **MVP note:** Components marked with `(planned)` are in the architecture but not yet implemented.

```mermaid
graph TB
    subgraph Frontend["Frontend Layer"]
        Dashboard["React Dashboard (planned)"]
    end

    subgraph API["API Gateway"]
        FastAPI["FastAPI<br/>REST + WebSocket"]
        Middleware["Middleware<br/>CORS, Auth, Tracing"]
    end

    subgraph Services["Microservices"]
        IncidentSvc["Incident Service"]
        DeploymentSvc["Deployment Service"]
        K8sSvc["Kubernetes Simulator"]
        CollectorSvc["Collector Service"]
        AISvc["AI Orchestrator"]
        WorkflowSvc["Workflow Engine (planned)"]
    end

    subgraph AI["AI Agents (6 specialized)"]
        LogAgent["Log Analysis Agent"]
        K8sAgent["K8s Analysis Agent"]
        MetricsAgent["Metrics Agent"]
        DeployAgent["Deployment Agent"]
        RootCauseAgent["Root Cause Agent"]
        RemediationAgent["Remediation Agent"]
    end

    subgraph EventBus["Event Bus"]
        Kafka["Apache Kafka"]
        Topics["Topics<br/>incidents.*<br/>deployments.*<br/>ai.*"]
    end

    subgraph Storage["Data Layer"]
        Postgres["PostgreSQL"]
        Redis["Redis"]
        InMemoryLogs["In-Memory Logs (simulated)"]
    end

    subgraph Observability["Observability"]
        Prometheus["Prometheus"]
        Grafana["Grafana"]
        OTEL["OpenTelemetry (planned)"]
    end

    subgraph Infra["Infrastructure"]
        K8s["Kubernetes"]
        AWS["AWS (planned)"]
        Terraform["Terraform"]
    end

    Dashboard --> FastAPI
    FastAPI --> IncidentSvc
    FastAPI --> DeploymentSvc
    FastAPI --> AISvc
    IncidentSvc --> Kafka
    DeploymentSvc --> Kafka
    Kafka --> AISvc
    AISvc --> LogAgent
    AISvc --> K8sAgent
    AISvc --> MetricsAgent
    AISvc --> DeployAgent
    LogAgent --> RootCauseAgent
    K8sAgent --> RootCauseAgent
    MetricsAgent --> RootCauseAgent
    DeployAgent --> RootCauseAgent
    RootCauseAgent --> RemediationAgent
    IncidentSvc --> Postgres
    DeploymentSvc --> Postgres
    FastAPI --> Redis
    CollectorSvc --> InMemoryLogs
    CollectorSvc --> Prometheus
    K8s --> Prometheus
    Prometheus --> Grafana
```

## Data Flow — Incident Lifecycle

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CI as CI/CD
    participant K8s as Kubernetes
    participant Mon as Prometheus
    participant GW as API Gateway
    participant IS as Incident Service
    participant Kafka as Kafka
    participant AI as AI Orchestrator
    participant Agents as 6 AI Agents
    participant RCA as Root Cause Agent
    participant Rem as Remediation Agent

    Dev->>CI: Push code
    CI->>K8s: Deploy
    K8s->>K8s: Pods crash (CrashLoopBackOff)
    K8s->>Mon: Metrics exposed
    Mon->>GW: Alert triggered
    GW->>IS: POST /incidents
    IS->>Kafka: incident.created
    Kafka->>AI: Analysis trigger
    AI->>Agents: Parallel analysis
    Agents->>RCA: Findings synthesized
    RCA->>Rem: Root cause determined
    Rem->>Kafka: remediation.proposed
    Kafka->>IS: Update incident
    IS->>GW: Incident resolved
```

## Multi-Agent Graph (LangGraph)

```mermaid
graph LR
    Start((Start)) --> LogAgent[Log Agent]
    Start --> K8sAgent[K8s Agent]
    Start --> MetricsAgent[Metrics Agent]
    Start --> DeployAgent[Deploy Agent]
    LogAgent --> RootCause[Root Cause Agent]
    K8sAgent --> RootCause
    MetricsAgent --> RootCause
    DeployAgent --> RootCause
    RootCause --> Remediation[Remediation Agent]
    Remediation --> End((End))
```

## Event-Driven Architecture

All inter-service communication flows through Kafka topics:

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `incidents.created` | Incident Service | AI Orchestrator, Notification Service | New incident detected |
| `incidents.updated` | Incident Service | Notification Service | Status change |
| `incidents.resolved` | Incident Service | Deployment Service | Incident resolved |
| `deployments.created` | Deployment Service | K8s Service | New deployment tracked |
| `deployments.failed` | Deployment Service | Incident Service | **Auto-creates incident** |
| `ai.analysis.started` | AI Orchestrator | Notification Service | Analysis begins |
| `ai.analysis.completed` | AI Orchestrator | Incident Service | Results ready |
| `ai.remediation.proposed` | AI Orchestrator | Incident Service, Deployment Service | Fix proposed |
| `notifications` | Notification Service | Slack, Jira, Email | External notifications |

## Design Patterns

### Implemented
- **Idempotent Consumers** — Every Kafka event carries an `event_id`. Consumers track processed IDs to avoid duplicate processing.
- **Dead-Letter Queue** — Failed messages are routed to `{topic}.dlq` for inspection, preventing poison messages from blocking the queue.
- **Event Sourcing (partial)** — Incident timeline events are captured as `IncidentEvent` records, enabling full audit trails.

### Planned
- **Outbox Pattern** — Database writes publish events atomically using the transactional outbox pattern.
- **Circuit Breaker** — External service calls (GitHub, Jira, Slack) use circuit breakers with exponential backoff.

## Key Design Decisions

- **Simulation mode**: Every external integration has a simulation fallback, making the system demo-able without any API keys
- **Dual-mode LLM**: Uses real OpenAI/Anthropic when keys are provided, falls back to deterministic simulation otherwise
- **Event sourcing for incident timeline**: All state changes are captured as events, enabling full audit trails
- **Parallel agent execution**: Four analysis agents run concurrently before root cause synthesis
- **MCP tool catalog**: All external systems (K8s, GitHub, Jira, Prometheus, Slack) exposed as MCP tools
